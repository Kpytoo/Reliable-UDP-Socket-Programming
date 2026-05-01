from socket import *
import struct
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


#Function that runs the server
def runServer(segmentSize):

    #Create the server UDP socket
    serverSocket = socket(AF_INET, SOCK_DGRAM)

    #Bind the socket to the server's address
    serverSocket.bind(serverAddress)

    #Set timeout for chunk packets (1 second)
    serverSocket.settimeout(1.0)

    #Listening to any incoming packets
    while True:
        try:
            #Retrieve the received packet
            clientPacket, clientAddress = serverSocket.recvfrom(2048)
            connectionIDClient, sequenceNumberClient, messageTypeClient, payloadClient = parsePacket(clientPacket)

            #Ignore if message is not a request
            if messageTypeClient != REQUEST:
                continue
            
            print("REQUEST message received!")

            #Get the file name requested
            filename = payloadClient.decode()
            
            #Check if the file exists, send an error if not
            if not os.path.exists(filename):
                errorPacket = createPacket(connectionIDClient, 0, ERROR, "File not found".encode())
                serverSocket.sendto(errorPacket, clientAddress)
                continue

            #Open the requested file
            with open(filename, "rb") as file:
                #Convert the file into bytes
                fileBytes = file.read()

                #Set a list called chunks, that will contain all the chunks file
                chunks = []
                for i in range(0, len(fileBytes), segmentSize):
                    chunks.append(fileBytes[i:i+segmentSize])

                #Start sequence number at 0
                sequenceNumber = 0
                packetNumber = 0
                #Send each chunk and wait for their ack packets
                for chunk in chunks:
                    print("---------------------")
                    retries = 0
                    #Send the chunks and wait for ack packet from the client (Stop And Wait)
                    while True:
                        #Create and send a chunk of the file
                        chunkPacket = createPacket(connectionIDClient, sequenceNumber, DATA, chunk)
                        serverSocket.sendto(chunkPacket, clientAddress)
                        print("Sent Packet #" + str(packetNumber) + " Retry #" + str(retries))
                        try:
                            
                            #Receive the ack packet from the client (no payload)
                            ackPacketClient , _ = serverSocket.recvfrom(HEADER_SIZE)
                            connectionIDACK, sequenceNumberACK, messageTypeACK, _ = parsePacket(ackPacketClient)

                            #Check if the right ack packet arrived
                            if connectionIDACK == connectionIDClient and sequenceNumberACK == sequenceNumber and messageTypeACK == ACK:
                                print("-- Received ACK for Packet #" + str(packetNumber))
                                packetNumber += 1
                                #If last chunk was acknowledged, break
                                print("Size: " + str(len(chunk)))
                                if len(chunk) < segmentSize:
                                    break
                                #Alternate sequence numbers between 0 and 1
                                if sequenceNumber == 0:
                                    sequenceNumber = 1
                                else:
                                    sequenceNumber = 0
                                break
                            else:
                                print("-- Received wrong ACK for Packet #" + str(packetNumber))
                                retries += 1
                        
                        #If timeout occurs for the DATA message (no ACK message received)
                        except timeout:
                            retries += 1
                            if retries > 10:
                                print("Too many retries, abort.")
                                break
                            print("**** SERVER TIMEOUT, resending DATA message...")
                            continue
            
            print("File has been transfered successfully!")
            break           
        #Ignore if timeout happens here
        except timeout:
            continue
    
    serverSocket.close()

if __name__ == "__main__":

    #Server must accept three arguments
    if len(sys.argv) != 5:
        print("Please enter: <40245452_Lab3_Server.py> <127.0.0.1> <12000> <--segment-size> <512>")
        sys.exit()

    #Parse the arguments
    serverIP = sys.argv[1]
    serverPort = int(sys.argv[2])

    if sys.argv[3] != "--segment-size":
        print("Missing: --segment-size")
        sys.exit()
    segmentSize = int(sys.argv[4])

    #Define server address
    serverAddress = (serverIP, serverPort)

    runServer(segmentSize)
