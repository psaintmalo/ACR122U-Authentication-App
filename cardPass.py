from defs import *
import random
from hashlib import sha256
from os import path
import time

passSector = 15
passKeyA = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]
defaultKeyA = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
passKeyB = [0x06, 0x05, 0x04, 0x03, 0x02, 0x01]
defaultKeyB = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
defaultAccessBytes = [0xFF, 0x07, 0x80, 0x69]
passAccessBytes = [0xFF, 0x07, 0x80, 0x69]

options = ["auth", "write", "setup", "clean", "add", "remove", "read", "toggleBeep"]
noPassOpt= ["setup", "read", "clear", "toggleBeep"]
menu_string = ("""\n  Options:
    auth: Attempt Authorization
    write: Write a new key to the pass data sector
    setup: Setup the pass data sector
    clean: Clean the pass data sector
    add: Add key data to auth database
    remove: Remove key data from auth database
    read: Read sector
    toogleBeep: Toggle beep on card detection
""")

def remove(key):
    newFile = ""
    hashString = sha256(key.encode()).hexdigest()
    if not path.exists("auths.txt"):
        print("Auth file doesnt exist")
        return False
    with open("auths.txt", "r") as file:
        lines = file.readlines()
        for line in lines:
            line = line[:-1]
            if(line != hashString):
                newFile += line
                newFile += "\n"

    with open("auths.txt", "w+") as file:
        file.write(newFile)

def auth(key):
    hashString = sha256(key.encode()).hexdigest()
    if not path.exists("auths.txt"):
        print("Auth file doesnt exist")
        return False
    with open("auths.txt", "r") as file:
        lines = file.readlines()
        for line in lines:
            line = line[:-1]
            if(line == hashString):
                return True

        return False

# TODO Change this
def hexKeyToString(key):
    string = ""
    for block in key:
        for byte in block[0]:
            string += str(byte)
            string += ","

    return string[:-1]

def addKey(key):
    if not auth(key):
        hashString = sha256(key.encode()).hexdigest()

        with open("auths.txt", "a+") as file:
            file.write(hashString)
            file.write("\n")
    else:
        print("Key already exists")

def readData(connection):
    result = []
    for i in range(3):
        result.append(readBlock(connection, passSector, i))
    return result

def readTrailer(connection):
    return readBlock(connection, passSector, 3)

def randomData():
    block = []

    for j in range(16):
        random_number = random.randint(0,256)
        hex_number = hex(random_number)
        block.append(random_number)

    return block


def setKey(connection):
    loadKey(connection, passKeyA)
    response = authenticate(connection, passSector*4)
    if response[1] == [0x90, 0x00]:
        return 0
    else:

        loadKey(connection, defaultKeyA)
        response = authenticate(connection, passSector*4)
        if response[1] == [0x90, 0x00]:
            return 1
        else:
            return -1


if __name__ == "__main__":

    lastAction = time.time() - 3
    beepState = True
    loopCounter = 0

    r = readers()
    if len(r) < 1:
        print("error: No readers available!")
        sys.exit()

    print("Available readers: ", r)

    reader = r[0]
    print("Using: ", reader)
    print("\n")
    while True:
        sleep(0.1)

        print(menu_string)
        opt = input(": ")
        split = opt.split(" ")
        if(len(split) == 2):
            opt = split[0]
            loopCounter = int(split[1])
        else:
            opt = split[0]
            loopCounter = 1
        print("\n")

        if opt == "exit":
            sys.exit()

        while(loopCounter != 0):
            # Cant remeber why I needed this, something to do with swapping cards
            # I think it gives time for the connection to reset but I cant remeber
            while(time.time() - lastAction < 3 ):
                sleep(0.2)

            cardtype = AnyCardType()
            cardrequest = CardRequest( timeout=10, cardType=cardtype )
            cardservice = cardrequest.waitforcard()

            connection = reader.createConnection()
            connection.connect()

            usingKey = setKey(connection)
            #print(response)
            if usingKey == -1:
                print("Unable to find key")
                sleep(2)
                continue
            elif usingKey == 1 and not opt in noPassOpt:
                print("Please run setup first")
                sleep(2)
                continue
            elif usingKey == 0 and opt == "setup":
                continue


            if(opt == "setup"):

                newTrailer = passKeyA + passAccessBytes + passKeyB
                response = writeAddrs(connection, passSector*4+3, newTrailer, trailer=True)
                printResponse(response)
                opt == "write"

            if(opt == "write"):

                for i in range(3):
                    newData = randomData()
                    response = write(connection, passSector, i, newData)
                    if(response[1] != [0x90, 0x00]):
                        print("Something went wrong while writing")
                        printResponse(response)
                        sleep(2)
                        continue

            elif(opt == "add"):
                key = hexKeyToString(readData(connection))
                if not auth(key):
                    addKey(key)
                else:
                    print("Key already present")

            elif(opt == "remove"):
                key = hexKeyToString(readData(connection))
                if auth(key):
                    remove(key)
                else:
                    print("Key not present")

            elif(opt == "clean"):
                key = hexKeyToString(readData(connection))
                if not auth(key):
                    for i in range(3):
                        newData = [0x00]*16
                        response = write(connection, passSector, i, newData)
                        if(response[1] != [0x90, 0x00]):
                            print("Something went wrong while writing")
                            printResponse(response)
                            sleep(2)
                            continue
                    newTrailer = defaultKeyA + defaultAccessBytes + defaultKeyB
                    response = writeAddrs(connection, passSector*4+3, newTrailer, trailer=True)
                    printResponse(response)
                else:
                    print("Remove key before cleaning data")

            elif(opt == "read"):
                keyType = "Default" if usingKey == 1 else "Pass"
                print("Active key: " + keyType)
                result = readData(connection)
                printBlocks(result)
                result = readTrailer(connection)
                printResponse(result)
                print("\n")

            elif(opt == "auth"):
                key = hexKeyToString(readData(connection))
                if auth(key):
                    print("Authenticated")
                    connection.transmit([0xFF, 0x00, 0x40, 0b11000011, 0x04, 0x01, 0x01, 0x02, 0x02])
                else:
                    print("Invalid")
                    connection.transmit([0xFF, 0x00, 0x40, 0b11000011, 0x04, 0x01, 0x04, 0x01, 0x02])

            elif(opt== "toggleBeep"):
                beepState = not beepState
                if beepState:
                    print("Enabling beep")
                else:
                    print("Disabling beep")
                r = setBeepOnCardDetection(connection, beepState)
                printResponse(r)

            #antennaEnable(connection, False)
            lastAction = time.time()
            loopCounter -= 1
            #connection.transmit([0xFF, 0x00, 0x40, 0b11000000, 0x04, 0x01, 0x01, 0x01, 0x02])
