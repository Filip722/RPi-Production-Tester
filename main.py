from ui import Ui_Dialog
import json
import os
import shutil
import sys
import time
import Adafruit_ADS1x15
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QDialog, QApplication
from random import randint

DEBUG = True  # set to get data from randint instead of real data from ADC ADS1115

ConfigDirectory = os.path.join(os.getcwd(), "Configs")  # Path to configs
remoteConfigDirectory = '//192.168.1.2/home/RpiTester/Configs'  # remote path to configs
refreshRate = 100  # refresh rate in milliseconds

CurrentBase = 1
CurrentTolerance = 0
VoltageBase = 1
VoltageTolerance = 0
AdditionalInfo = ""

adc_divider = [1, 1]  # set this to calibrate according to dividers / shunts
voltageMeasured = [0, 0]


class GetADCThread(QThread):

    voltageSignal = pyqtSignal(str)
    currentSignal = pyqtSignal(str)
    DeviationCurrentLabel = pyqtSignal(str)
    DeviationVoltageLabel = pyqtSignal(str)

    pushButtonCurrent = pyqtSignal(str)
    pushButtonVoltage = pyqtSignal(str)
    pushButtonALL = pyqtSignal(str)

    def __init__(self):
        QThread.__init__(self)
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            QThread.msleep(refreshRate)

            if DEBUG is False:
                for i in range(0, 1):
                    adc = Adafruit_ADS1x15.ADS1115().read_adc(i, gain=1)
                    voltageMeasured[i] = adc / 65535 * 4.096 * adc_divider[i]
            else:
                voltageMeasured[0] = randint(20, 28)
                voltageMeasured[1] = randint(200, 400)

            self.voltageSignal.emit(f'{format(voltageMeasured[0], ".2f")}')
            self.currentSignal.emit(f'{format(voltageMeasured[1], ".2f")}')

            minCurrent = CurrentBase / 100 * (100 - CurrentTolerance)
            maxCurrent = CurrentBase / 100 * (100 + CurrentTolerance)
            minVoltage = VoltageBase / 100 * (100 - VoltageTolerance)
            maxVoltage = VoltageBase / 100 * (100 + VoltageTolerance)

            if voltageMeasured[0] > minVoltage and voltageMeasured[0] < maxVoltage:
                self.pushButtonVoltage.emit("border-radius:25px; background-color: rgb(0,255,0);")
                isVoltageOK = True
            else:
                self.pushButtonVoltage.emit("border-radius:25px; background-color: rgb(255,0,0);")
                isVoltageOK = False

            if voltageMeasured[1] > minCurrent and voltageMeasured[1] < maxCurrent:
                self.pushButtonCurrent.emit("border-radius:25px; background-color: rgb(0,255,0);")
                isCurrentOK = True
            else:
                self.pushButtonCurrent.emit("border-radius:25px; background-color: rgb(255,0,0);")
                isCurrentOK = False

            if isCurrentOK is True and isVoltageOK is True:
                self.pushButtonALL.emit("border-radius:50px; background-color: rgb(0,255,0);")
            else:
                self.pushButtonALL.emit("border-radius:50px; background-color: rgb(255,0,0);")

            VoltageDeviation = (1 - (voltageMeasured[0] / VoltageBase)) * 100
            VoltageDeviation = f'{format(VoltageDeviation, ".2f")}'
            self.DeviationVoltageLabel.emit(f'{VoltageDeviation}%')

            CurrentDeviation = (1 - (voltageMeasured[1] / CurrentBase)) * 100
            CurrentDeviation = f'{format(CurrentDeviation, ".2f")}'
            self.DeviationCurrentLabel.emit(f'{CurrentDeviation}%')


class AppWindow(QDialog):

    def __init__(self):

        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.show()
        self.getBoards()

        self.ui.comboBoxDirs.currentIndexChanged.connect(self.getConfigs)
        self.ui.comboBoxConfigs.currentIndexChanged.connect(self.loadConfig)
        self.ui.pushButtonLoad.clicked.connect(self.copyConfigs)

        self.getADCThread = GetADCThread()
        self.getADCThread.start()
        self.getADCThread.voltageSignal.connect(self.ui.labelVoltageMeasured.setText)
        self.getADCThread.currentSignal.connect(self.ui.labelCurrentMeasured.setText)

        self.getADCThread.DeviationCurrentLabel.connect(self.ui.CurrentDeviationLabel.setText)
        self.getADCThread.DeviationVoltageLabel.connect(self.ui.VoltageDeviationLabel.setText)

        self.getADCThread.pushButtonCurrent.connect(self.ui.pushButtonCurrent.setStyleSheet)
        self.getADCThread.pushButtonVoltage.connect(self.ui.pushButtonVoltage.setStyleSheet)
        self.getADCThread.pushButtonALL.connect(self.ui.pushButtonALL.setStyleSheet)

        self.ui.pushButtonALL.setStyleSheet("border-radius:50px; background-color: rgb(255,0,0);")

        app.processEvents()

    def loadConfig(self):
        if self.ui.comboBoxConfigs.currentText() is not "":
            configPATH = os.path.join(os.path.join(ConfigDirectory, self.ui.comboBoxDirs.currentText()),
                                      self.ui.comboBoxConfigs.currentText()) + '.config'
            with open(configPATH, 'r') as file:
                config = file.read()

            config = json.loads(config)
            global CurrentBase, CurrentTolerance, VoltageBase, VoltageTolerance, AdditionalInfo

            CurrentBase = config["CurrentBase"]
            CurrentTolerance = config["CurrentTolerance"]

            VoltageBase = config["VoltageBase"]
            VoltageTolerance = config["VoltageTolerance"]

            AdditionalInfo = config['AdditionalInfo']

            self.ui.labelAdditionalInfo.setText(AdditionalInfo)
            self.ui.labelSetCurrentTo.setText(f'{format(CurrentBase, ".2f")}')
            self.ui.labelSetVoltageTo.setText(f'{format(VoltageBase, ".2f")}')

    def copyConfigs(self):
        shutil.rmtree(ConfigDirectory, ignore_errors=True)
        for item in os.listdir(remoteConfigDirectory):
            shutil.copytree(remoteConfigDirectory, ConfigDirectory)
        self.getBoards()

    def getConfigs(self):
        self.ui.comboBoxConfigs.clear()
        self.ui.comboBoxConfigs.addItem("")  # to make sure user selects a config!
        for file in os.listdir(os.path.join(ConfigDirectory, self.ui.comboBoxDirs.currentText())):
            if file.endswith(".config"):
                self.ui.comboBoxConfigs.addItem(file[:-7])

    def getBoards(self):
        self.ui.comboBoxDirs.clear()
        self.ui.comboBoxDirs.addItem("")  # to make sure user selects a board!
        for file in os.listdir(ConfigDirectory):
            if os.path.isdir(os.path.join(ConfigDirectory, file)):
                self.ui.comboBoxDirs.addItem(file)


app = QApplication(sys.argv)
app.setStyle('Fusion')
w = AppWindow()
w.show()
sys.exit(app.exec_())
