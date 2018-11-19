# Automation
You can write automation script on the GUI for automatic control of the microscope.

# API functions

## Camera settings

### toggleCamera()

### setCameraParam(key, value)

### setExposure(t)

### setTrigger(source)

## Laser control

### setLaser(name, on_off)

### setLaserPower(name, power)

### setDigitalModulation(on_off)

### setDigitalPower(name, power)

## Scanning control

### setScanMode(mode)

### setScanRepeat(repeat)

### loadScan(filePath=None)

### startScan()

### stopScan()

### waitUntilScanStop()

### saveScan(filePath=None)

## Recording

### specifyFileName(filePath)

### setRecordMode()

### startRecord()

### stopRecord(wait=True, timeout=None)

## Automation

### runScript(scriptPath=None)

### loadScript(scriptPath=None)

### saveScript()

## Utilities

### wait(seconds)
