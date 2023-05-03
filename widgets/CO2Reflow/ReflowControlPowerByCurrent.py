from functions.HMP4040Control import HMP4040Visa
import time


class ReflowControlPowerByCurrent:
    def __init__(self):
        # ----------- HMP4040 Control -----------
        self.HMP4040 = HMP4040Visa(port = 'ASRL6::INSTR')
        self.HMP4040.setOutput(4)
        self.HMP4040.outputState(2)
        start_time = time.time()
        #
        del_I = 1
        for i in range(6,10,del_I):
            self.HMP4040.setCurrent(i*1e-3)
            print(i)
        print("--- %s seconds ---" % (time.time() - start_time))

if __name__ == "__main__":
    o=ReflowControlPowerByCurrent()



