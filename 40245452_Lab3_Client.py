from socket import * #To use socket programming
import struct #To create custom header (added in payload)
import random
import os
import sys


#Define the message types as integers
REQUEST = 0
DATA = 1
ACK = 2
ERROR = 3


#Header information
HEADER_FORMAT = '!IBBI'
HEADER_SIZE = struct.calcsize("!IBBI")


#Function that creates a packet by combining the header and the data, in bytes
#(Size of header is 10 bytes because of IBBI)
#(I = Unsigned INT - 4 bytes)
#(B = Unsigned CHAR - 1 byte)
def createPacket(connectionID, sequenceNumber, messageType, payloadBytes):
    #Get the length of the encoded payload
    payloadLengthBytes = len(payloadBytes)
    #Pack all the header info into bytes
    header = struct.pack(HEADER_FORMAT, connectionID, sequenceNumber, messageType, payloadLengthBytes)
    #Return the header bytes plus the payload bytes
    return header + payloadBytes


#Function that parses a received packet
def parsePacket(packet):
    #Unpack the header information from the received packet
    connectionID, sequenceNumber, messageType, payloadLentgthBytes = struct.unpack(HEADER_FORMAT, packet[:HEADER_SIZE])
    #Retrieve the payload from the received packet
    payload = packet[HEADER_SIZE:HEADER_SIZE + payloadLentgthBytes]
    return connectionID, sequenceNumber, messageType, payload


#Function that runs the client
def runClient(filename, segmentSize):
    #Create the client UDP socket
    clientSocket = socket(AF_INET, SOCK_DGRAM)

    #Create timeout for request message (1 second)
    clientSocket.settimeout(1.0)

    #Set up connection ID
    connectionID = random.randint(0, 2**32 - 1)

    #Start sequence number at 0
    sequenceNumber = 0

    #Send request message
    print("Sending REQUEST message...")
    requestPacket = createPacket(connectionID, 0, REQUEST, filename.encode())
    clientSocket.sendto(requestPacket, serverAddress)
    requestHasBeenReceivedByServer = False

    #Create a file for the client
    clientFile = "client_" + filename
    with open(clientFile, "wb") as file:
        #Listening to any incoming packets
        packetNumberReceived = 0
        while True:
            try:
                #Retrieve the received packet
                serverPacket, _ = clientSocket.recvfrom(segmentSize + HEADER_SIZE)
                connectionIDServer, sequenceNumberServer, messageTypeServer, payloadServer = parsePacket(serverPacket)
                
                #Ignore non corresponding packets
                if connectionIDServer != connectionID:
                    continue
                
                #If the sequence number isn't the same. Resend ACK.
                if sequenceNumberServer != sequenceNumber and messageTypeServer == DATA:
                    #Create and resend a respective ACK packet
                    ackPacket = createPacket(connectionID, sequenceNumberServer, ACK, "".encode())
                    clientSocket.sendto(ackPacket, serverAddress)
                    continue

                #If the server sends an error packet
                if messageTypeServer == ERROR:
                    print("Server Error: " + payloadServer.decode())
                    break
                
                #Ignore if at this point it's not DATA
                if messageTypeServer != DATA:
                    continue
                requestHasBeenReceivedByServer = True
                
                #Write the payload to the file
                file.write(payloadServer)

                #Create and send a respective ACK packet
                ackPacket = createPacket(connectionID, sequenceNumber, ACK, "".encode())
                clientSocket.sendto(ackPacket, serverAddress)
                print("Packet received #" + str(packetNumberReceived) +": " + str(len(payloadServer)) + " Bytes")
                
                packetNumberReceived += 1

                #Alternate sequence numbers between 0 and 1
                if sequenceNumber == 0:
                    sequenceNumber = 1
                else:
                    sequenceNumber = 0

                #Check if the last packet arrived (if the payload is smaller than the segment size)
                if len(payloadServer) < segmentSize:
                    break
            
            #If timeout occurs for the request message (no DATA message received)
            except timeout:
                if not requestHasBeenReceivedByServer:
                    print("CLIENT TIMEOUT, resending REQUEST message...")
                    requestPacket = createPacket(connectionID, 0, REQUEST, filename.encode())
                    clientSocket.sendto(requestPacket, serverAddress)
    
    #Print that the transfer has been successful
    print("File has been transfered. Total size: " + str(os.path.getsize(clientFile)) + " Bytes")
    clientSocket.close()


if __name__ == "__main__":

    #Client must accept four arguments
    if len(sys.argv) != 6:
        print("Please enter: <40245452_Lab3_Client.py> <127.0.0.1> <12000> <filename> <--segment-size> <512>")
        sys.exit()

    #Parse the arguments
    serverIP = sys.argv[1]
    serverPort = int(sys.argv[2])
    fileName = sys.argv[3]

    if sys.argv[4] != "--segment-size":
        print("Missing: --segment-size")
        sys.exit()
    segmentSize = int(sys.argv[5])

    #Define server address
    serverAddress = (serverIP, serverPort)

    runClient(fileName, segmentSize)


