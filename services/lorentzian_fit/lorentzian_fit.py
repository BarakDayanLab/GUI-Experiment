import os
import time
import glob
import numpy as np
from scipy import optimize, spatial
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.signal import savgol_filter

# See how to do this in Excel:
# https://www.youtube.com/watch?v=sp3miOY-emo&ab_channel=Edmerls


class LorentzianFit:

    def __init__(self):
        pass

    def load_rb_lines_data(self, data_file, inverse=False):
        # Load data from numpy file
        try:
            self.rb_data_points = np.load(data_file)
        except Exception as err:
            print('Failed to load data from %s (%s)' % (data_file, err))
            raise err
        if inverse:
            self.rb_data_points = -1 * self.rb_data_points
        pass

    def load_data(self, data_file, inverse=False):
        # Load data from numpy file
        try:
            self.data_points = np.load(data_file)
        except Exception as err:
            print('Failed to load data from %s (%s)' % (data_file, err))
            raise err
        if inverse:
            self.data_points = -1 * self.data_points

    def set_data(self, data, inverse=False):
        self.data_points = data
        if inverse:
            self.data_points = -1 * self.data_points

    def model(self, x, a, b):
        return a*(x*x + b)

    def lorentzian_other(self, f, k_ex, k_tot, h, f_offset, offset, amp):
        '''
        f - the data
        k_ex, k_tot, h, f_offset - Hz
        amp, offset - [V]
        '''
        delta = f - f_offset
        z = offset + amp * np.power(np.abs(2 * k_ex * h / ((1j * delta + k_tot) ** 2 + h ** 2)), 2)
        return z

    #def reflection_func(self, f, y, k_ex, k_i, h, f_offset, y0):
    def lorentzian_dorko(self, f, y, k_ex, k_i, h, f_offset, y0):
        z = y0 + np.power(np.abs(2 * k_ex * h /
                                 (np.power((1j * (f - f_offset) + (k_i + k_ex)), 2) + np.power(h, 2))), 2) - y
        return z

    def lorentzian(self, x, x0, width, amp, y0, a, b):
        nominator = np.power(width, 2)
        denominator = np.power(x-x0, 2) + nominator
        y = y0-amp*(nominator/denominator)

        y = y + a + b * x  # DC Coupling

        return y

    def myfunc(self, str, value):
        return '%d-%s' % (value, str)

    def deduce_frame(self, troughs, peaks):

        MIN = 0
        MAX = len(self.data_points)-1

        if len(troughs) == 0 and len(peaks) == 0:
            return None, "N/A"

        # Create a merged-sorted list of the troughs and peaks (pad with zeros, as we will sort it as strings
        troughs = list(map(lambda x: '%03d-T' % x, troughs))
        peaks = list(map(lambda x: '%03d-P' % x, peaks))
        merged_list = troughs + peaks
        merged_list.sort()

        # Remove duplicates
        deduped_list = [merged_list[0]]
        prev = merged_list[0][-1]
        for i in range(1, len(merged_list)):
            if merged_list[i][-1] != prev:
                deduped_list.append(merged_list[i])
            prev = merged_list[i][-1]
        merged_list = deduped_list

        # Decode and create pattern (e.g. "PTP", or "TP", or "PTPTP")
        pattern = "".join(list(map(lambda x: x[-1], merged_list)))

        # If we have only one peak OR one trough (e.g. "P" or "T")
        if len(pattern) == 1:
            if pattern == "P":
                frame = [0, int(merged_list[0][0:-2])]
            else:  # "T"
                frame = [0, len(self.data_points)-1]
        # PT -> Peak-to-Max , TP -> Start-to-Peak
        elif len(pattern) == 2:
            if pattern == 'PT':
                frame = [int(merged_list[0][0:-2]), MAX]
            else:  # "TP"
                frame = [MIN, int(merged_list[1][0:-2])]
        # PTP -> Peak-to-Peak , TPT -> Min-To-Peak
        elif len(pattern) == 3:
            if pattern == 'PTP':
                frame = [int(merged_list[0][0:-2]), int(merged_list[2][0:-2])]
            else:  # "TPT"
                frame = [MIN, int(merged_list[1][0:-2])]
        # PTPT -> Peak-to-Peak , TPTP -> Start-to-Peak  (or PTPTP/TPTPT)
        elif len(pattern) >= 4:
            if pattern.startswith('PTPT'):
                frame = [int(merged_list[0][0:-2]), int(merged_list[2][0:-2])]
            else:  # "TPTP"
                frame = [int(merged_list[1][0:-2]), int(merged_list[3][0:-2])]
        else:
            pass  # Should never get here

        return frame, pattern

    def fit(self, fev, prominence):

        x_data = np.arange(0.0, 1.0, 1/1024)
        y_data = self.data_points

        #--------------------------------
        # Find troughs & peaks on signal
        #--------------------------------
        troughs, t_properties = find_peaks(y_data*-1, prominence=prominence)
        peaks, p_properties = find_peaks(y_data, prominence=prominence)

        # Get two-peaks that frame the resonance (decided based on troughs and peaks)
        peaks, pattern = self.deduce_frame(troughs, peaks)

        if peaks is None:
            return None  # No peaks or troughs -> No fit

        # Crop data - from peak to peak
        #delta = int((peaks[1]-peaks[0])*0.2)
        delta = 0
        x_framed_data = x_data[peaks[0]+delta:peaks[1]-delta]
        y_framed_data = y_data[peaks[0]+delta:peaks[1]-delta]

        #------------------------
        # Find Lorentzian
        #------------------------
        try:
            t0 = time.time()
            x0_left = x_data[peaks[0]]
            x0_right = x_data[peaks[1]]
            max_width = x0_right - x0_left
            bounds = ([x0_left, 0.0, 0, 0.01, -0.03, -0.1], [x0_right, max_width, np.inf, np.inf, 0.03, 0.1])  # x0, width, amp, y0, a, b
            popt, pcov = optimize.curve_fit(self.lorentzian, x_framed_data, y_framed_data, p0=None, bounds=bounds, maxfev=fev)
            t = time.time() - t0
        except:
            return None  # Failed to create fit

        # Prepare the curve-fit data
        x0 = popt[0]
        width = popt[1]
        amp = popt[2]
        y0 = popt[3]
        a = popt[4]
        b = popt[5]
        y_fit_data = self.lorentzian(x_framed_data, x0, width, amp, y0, a, b)

        return y_fit_data

    def deduce_rb_lines_peaks(self, peaks):
        if len(peaks) < 4:
            return peaks

        # Find the cut-off point
        peaks_y = list(self.rb_data_points[peaks])
        peaks_y.sort(reverse=True)
        cutoff = peaks_y[2]

        # Return those peaks that are higher or equal to the cutoff point
        the_three = list(filter(lambda x: self.rb_data_points[x] >= cutoff, peaks))

        return the_three

    # Find RB lines peaks
    def analyze_rb_lines(self, title, hold=False):

        prominence = 0.0024

        plt.figure(title)

        # Set X/Y-axis values
        x_data = np.arange(0.0, 1.0, 1/1024)
        y_data = self.rb_data_points

        # Find peaks on this one:
        #peaks, p_properties = find_peaks(y_data)
        peaks, p_properties = find_peaks(y_data, prominence=prominence)

        peaks = self.deduce_rb_lines_peaks(peaks)

        # Crop data - from peak to peak
        delta = 0
        x_framed_data = x_data[peaks[0]+delta:peaks[1]-delta]
        y_framed_data = y_data[peaks[0]+delta:peaks[1]-delta]

        plt.title(title)

        # Plot the signal line
        plt.plot(x_data, y_data, '-', color='blue', label='data')

        # Plot the prominence line
        y_prom = np.zeros_like(x_data)+prominence
        plt.plot(x_data, y_prom, "--", color="gray")

        # Plot the peaks
        plt.plot(x_data[peaks], y_data[peaks], "x", color="red")

        # Figure Cosmetics...
        axis = plt.gca()
        axis.spines['right'].set_visible(False)
        axis.spines['top'].set_visible(False)

        # Name the x/y-axis
        plt.xlabel('Time [ms]')
        plt.ylabel('Voltage [V]')

        plt.xticks(np.arange(0, 1, step=0.1))
        plt.yticks(np.arange(-0.15, 0.15, step=0.03))

        axis.legend()

        self.maximize_figure()

        plt.show(block=hold)

        pass

    def plot_fit(self, fev, title, prominence, hold):

        plt.figure(title)

        # Set X/Y-axis values
        x_data = np.arange(0.0, 1.0, 1/1024)
        y_data = self.data_points

        # Smooth the signal line
        #y_data = savgol_filter(y_data, 51, 3)  # window size 51, polynomial order 3

        #--------------------------------
        # Find troughs & peaks on signal
        #--------------------------------
        troughs, t_properties = find_peaks(y_data*-1, prominence=prominence)
        peaks, p_properties = find_peaks(y_data, prominence=prominence)

        print('Peaks: %d | Troughs: %d' % (len(peaks), len(troughs)))

        # Get two-peaks that frame the resonance (decided based on troughs and peaks)
        peaks, pattern = self.deduce_frame(troughs, peaks)

        if peaks is None:
            # Plot the signal line
            plt.plot(x_data, y_data, '-', color='blue', label='data')
            self.maximize_figure()
            plt.show(block=hold)
            return

        # Crop data - from peak to peak
        #delta = int((peaks[1]-peaks[0])*0.2)
        delta = 0
        x_framed_data = x_data[peaks[0]+delta:peaks[1]-delta]
        y_framed_data = y_data[peaks[0]+delta:peaks[1]-delta]

        #------------------------
        # Find Lorentzian
        #------------------------
        t0 = time.time()
        x0_left = x_data[peaks[0]]
        x0_right = x_data[peaks[1]]
        max_width = x0_right - x0_left
        bounds = ([x0_left, 0.0, 0, 0.01, -0.03, -0.1], [x0_right, max_width, np.inf, np.inf, 0.03, 0.1])  # x0, width, amp, y0, a, b
        popt, pcov = optimize.curve_fit(self.lorentzian, x_framed_data, y_framed_data, p0=None, bounds=bounds, maxfev=fev)
        t = time.time() - t0

        # Prepare the curve-fit data
        x0 = popt[0]
        width = popt[1]
        amp = popt[2]
        y0 = popt[3]
        a = popt[4]
        b = popt[5]
        y_fit_data = self.lorentzian(x_framed_data, x0, width, amp, y0, a, b)

        plt.title("p=%s, t=%.2f, x0=%.2f, width=%.2f, amp=%f, y0=%.2f, a=%.3f, b=%.3f" % (pattern, t, x0, width, amp, y0, a, b))

        # Plot the signal line
        plt.plot(x_data, y_data, '-', color='blue', label='data')

        # Plot the Lorentzian curve-fit line
        plt.plot(x_framed_data, y_fit_data, '-', color='orange', label='fit')

        # Plot the window frame we used for the Lorentzian curve-fit
        plt.plot(x_framed_data, y_framed_data, '-', color='red', label='framed')

        # Plot the prominence line
        y_prom = np.zeros_like(x_data)+prominence
        plt.plot(x_data, y_prom, "--", color="gray")

        # Plot the peaks
        plt.plot(x_data[peaks], y_data[peaks], "x", color="red")

        # Plot my "manual" fit attempt
        #plt.plot(x_data, self.lorentzian_dror(x=x_data, x0=0.31, width=0.2, amp=0.2, y0=0.13), '-', color='black')

        # Figure Cosmetics...
        axis = plt.gca()
        axis.spines['right'].set_visible(False)
        axis.spines['top'].set_visible(False)

        # Name the x/y-axis
        plt.xlabel('Time [ms]')
        plt.ylabel('Voltage [V]')

        plt.xticks(np.arange(0, 1, step=0.1))
        plt.yticks(np.arange(-0.15, 0.15, step=0.03))

        axis.legend()

        self.maximize_figure()

        plt.show(block=hold)

        pass

    def maximize_figure(self):
        bg = plt.get_backend()
        if bg == 'QtAgg' or bg == 'QT4Agg':
            figManager = plt.get_current_fig_manager()
            figManager.window.showMaximized()
        elif bg == 'TkAgg':
            mng = plt.get_current_fig_manager()
            mng.resize(*mng.window.maxsize())
            mng.window.state('zoomed')  # works fine on Windows!
        elif bg == 'wxAgg':
            mng = plt.get_current_fig_manager()
            mng.frame.Maximize(True)


    @staticmethod
    def plot_lorentzian(hold):

        plt.figure("Lor")

        x_data = np.arange(0, 1.0, 1/1024)
        y_data = self.lorentzian(x=x_data, x0=0.5, width=0.1, amp=20, y0=-0.2)

        plt.plot(x_data, y_data, '-', color='orange', label='data')

        plt.show(block=hold)

    @staticmethod
    def run_on_folder(folder_path, continue_from=None):
        FEV = 500000

        plt.ion()

        folder_path = os.path.join(folder_path, '*.npy')
        files = glob.glob(folder_path)
        files.sort()

        i = 1
        skip = (continue_from != None)
        for file in files:
            if skip and file.find(continue_from) != -1:
                skip = False
            if skip:
                continue

            lf = LorentzianFit()
            lf.load_data(file, True)
            i = i + 1
            print('Trying to fit %s' % file)

            fit = lf.fit(FEV, 0.02)

            lf.plot_fit(FEV, 'Plot #%d - %s' % (i, file), 0.02, True)
        pass

    @staticmethod
    def run_specific_test(file_path):
        FEV = 500000
        lf = LorentzianFit()
        lf.load_data(file_path, True)  # Load the file and inverse it
        lf.plot_fit(FEV, '%s' % file_path, 0.02, True)

    @staticmethod
    def run_tests():
        """
        Runs various spectrum cases we have - attempts to find the fit
        """

        FEV = 500000

        cwd = os.getcwd()
        base_dir = os.path.join(cwd, 'lorentzian_fit', 'tests')
        data_files = [
            ['ALL_PEAKS', 'ALL_PEAKS_20230719-190922_figure.npy'],
            ['LOTS_OF_PEAKS', 'LOTS_OF_PEAKS_20230719-102918_figure.npy'],
            ['CLASSIC', 'CLASSIC_20230720-170058_spectrum.npy'],
            ['DOUBLE U', 'DOUBLE_U_20230719-104418_spectrum.npy'],
            ['NO CLEAR PEAKS', 'NO_CLEAR_PEAKS_20230719-040916_spectrum.npy'],
            #['FLAT LINE', 'FLAT_LINE_20230719-014415_spectrum.npy'],
            ['ALL PEAKS', 'ALL_PEAKS_20230719-190922_figure.npy']
        ]

        lf = LorentzianFit()

        for i in range(0, len(data_files)):
            file_name = data_files[i][0]
            file_path = os.path.join(base_dir, data_files[i][1])
            lf.load_data(file_path, True)  # Load the file and inverse it
            lf.plot_fit(FEV, 'Plot #%d - %s' % (i, file_name), 0.02, i == len(data_files) - 1)

        return

    @staticmethod
    def run_rb_lines_test(file):
        lf = LorentzianFit()
        lf.load_rb_lines_data(file, False)
        res = lf.analyze_rb_lines('Rb Lines Analysis', True)
        pass

if __name__ == "__main__":

    # Test for plotting the Lorentzian function on predefined spectrum files we have
    #LorentzianFit.run_tests()

    LorentzianFit.run_rb_lines_test(r'U:\Lab_2023\Experiment_results\QRAM\Cavity_Spectrum\20230808\20230808-150209_rb_lines_spectrum.npy')

    #LorentzianFit.plot_lorentzian(True)
    pass
