from smartcard.System import readers
from smartcard.util import toHexString
from smartcard.ATR import ATR
from smartcard.CardType import AnyCardType
from smartcard.Exceptions import NoCardException
from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest
from smartcard.CardConnectionObserver import ConsoleCardConnectionObserver
import sys
from math import floor
from time import sleep

def accessEncoder(arr):
    pass

def accessDecoder(arr):
    pass

def antennaEnable(connection, mode):
    ANTENNA_POWER_COMMAND = [0xFF, 0x00, 0x00, 0x00, 0x04, 0xD4, 0x32, 0x01]
    if mode:
        connection.transmit(ANTENNA_POWER_COMMAND + [0x01])
    else:
        connection.transmit(ANTENNA_POWER_COMMAND + [0x00])

def setBeepOnCardDetection(connection, doBeep):
    POLL_BUZ_STATUS = 0xFF if doBeep else 0x00
    SET_BEEP_COMMAND = [0xFF, 0x00, 0x52] + [POLL_BUZ_STATUS] + [0x00]
    data, sw1, sw2 = connection.transmit(SET_BEEP_COMMAND)
    return [[], [sw1, sw2]]

def writeKeyA(connection, keyA, sector):

    if(len(keyA) != 6):
        return [[], [sw1, sw2]]

    authenticate(connection, sector*4 + 3)
    sectorTrailer = readBlock(connection, sector, 3)
    if(sectorTrailer[1] != [0x90, 0x00]):
        return [[], [0x63, 0x00]]

    newTrailer = keyA + sectorTrailer[0][6:]
    return write(connection, sector, 3, newTrailer, trailer=True)

def loadKey(connection, key, location=0x00):

    if(location != 0x00 and location != 0x01):
        return [[], [0x63, 0x00]]
    elif(len(key) != 6):
        return [[], [0x63, 0x00]]

    LOAD_COMMAND = [0xFF, 0x82, 0x00]
    KEY_LOCATION = location # 0x00 - 0x01
    KEY = key
    COMMAND = LOAD_COMMAND + [KEY_LOCATION, 0x06] + KEY

    data, sw1, sw2 = connection.transmit(COMMAND)

    return [[], [sw1, sw2]]


def authenticate(connection, addrs, keyAddress=0x00, keyType=0x60):

    if ( keyAddress != 0x00 and keyAddress != 0x01):
        return [[], [0x63, 0x00]]
    elif ( keyType != 0x60 and keyType != 0x61):
        return [[], [0x63, 0x00]]

    AUTH_COMMAND = [0xFF, 0x86, 0x00, 0x00, 0x05]

    VER = 0x01
    BYTE_2 = 0x00
    BLOCK_ADDRS = addrs
    KEY_TYPE = keyType # 0x60 = KeyA, 0x61 = KeyB
    KEY_NUM = keyAddress # 0x00 - 0x01, Key location
    AUTH_DATA_BYTES = [VER, BYTE_2, BLOCK_ADDRS, KEY_TYPE, KEY_NUM]

    COMMAND = AUTH_COMMAND + AUTH_DATA_BYTES

    data, sw1, sw2 = connection.transmit(COMMAND)
    return [[], [sw1, sw2]]


def writeAddrs(connection, addrs, data, trailer=False):

    if(len(data) != 16):
        return [[], [0x63, 0x00]]

    elif(addrs > 63):
        return [[], [0x63, 0x00]]
    elif(addrs == 0):
        #print("Cannot modify first block!")
        return [[], [0x63, 0x00]]
    elif(addrs % 4 == 3 and not trailer):
        #print("Cannot modify the sector trailer!")
        return [[], [0x63, 0x00]]
    elif(trailer and addrs % 4 != 3):
        #print("Not a sector trailer!")
        return [[], [0x63, 0x00]]

    if authenticate(connection, addrs) == [[], [0x63, 0x00]]:
        return [[], [0x63, 0x00]]


    WRITE_COMMAND = [0xFF, 0xD6, 0x00]
    BLOCK_ADDRS = addrs
    N_BYTES = 0x10
    DATA = data

    COMMAND = WRITE_COMMAND + [BLOCK_ADDRS, N_BYTES] + DATA

    response, sw1, sw2 = connection.transmit(COMMAND)

    return [response, [sw1, sw2]]


def write(connection, sector, block, data, trailer=False):

    addrs = sector*4 + block
    return writeAddrs(connection, addrs, data, trailer)



def readBlock(connection, sector, block, auth=True, bytesToRead=0x10):

    if auth:
        if authenticate(connection, sector*4 + block) == [[], [0x63, 0x00]]:
            return [[], [0x63, 0x00]]

    if block > 3 or block < 0:
        return [[], [0x63, 0x00]]
    elif sector < 0 or sector > 15:
        return [[], [0x63, 0x00]]

    READ_COMMAND = [0xFF, 0xB0, 0x00]
    BLOCK_ADDRS = sector*4 + block
    BYTES_TO_READ = bytesToRead

    COMMAND = READ_COMMAND + [BLOCK_ADDRS, BYTES_TO_READ]

    data, sw1, sw2 = connection.transmit(COMMAND)

    result = [data, [sw1, sw2]]

    if (sw1, sw2) == (0x63, 0x00):
        print("Status: The operation failed. Maybe auth is needed.")

    return result


def readSector(connection, sector):

    if authenticate(connection, sector*4 + block) == [[], [0x63, 0x00]]:
        return [[], [0x63, 0x00]]
    result = []
    for i in range(4):
        rData = readBlock(connection, sector, i, auth=False)
        result.append(rData)

    return result


def printSector(connection, sector):
    sectorData = readSector(connection, sector)
    if(len(sectorData) != 4):
        print("Error while reading sector")

    else:
        for block in sector:
            data = block[0]
            sw1, sw2 = block[1]
            print(toHexString(data), " | ", sw1, " ", sw2)


def printBlocks(arr):

    for block in arr:
        data = block[0]
        sw1, sw2 = block[1]
        print(toHexString(data), " | ", toHexString([sw1, sw2]))#, " | ", "".join(chr(d) for d in data))

    print("-----------------------------------------------")

def printResponse(arr):
    data = arr[0]
    sw1, sw2 = arr[1]
    print(toHexString(data), " | ", toHexString([sw1, sw2]))
