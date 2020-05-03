# This file should be in the same folder as mugen.exe to work properly

from pynput.keyboard import Controller
from pynput.keyboard import Key
from time import sleep
from ReadWriteMemory import ReadWriteMemory
import os
import signal

logfile = "mugen.log" # Path to log file to monitor
badcharfile = "badchar.txt" # Path to a file containing list of bad characters

OK = "r"            # Button to press for selecting
NEXT = 'd'          # Button to press to move right
PREV = 'a'          # Button to press to move left
UP = 'w'            # Button to press to move up
DOWN = 's'          # Button to press to move down

ROUNDS = 2          # Rounds won required to win the match
HOLDTIME = 0.1      # Time to hold r button
debug = True        # Enable debug prints


# Memory reader info
PROCESS_NAME = 'mugen.exe'
BASE_ADDRESS = 0x00400000
WIN_ADDRESS  = BASE_ADDRESS + 0x001040E8
THREADSTACK0 = 0x0019FF7C - 0x418


class MugenOperator():

    def __init__(self):
        self.player1_chars = []
        self.player2_chars = []
        self.rwm = ReadWriteMemory()
        self.output_keyboard = Controller()
        self.char1 = -1
        self.char2 = -1
        self.winner = -1
        self.reset()
        
    def reset(self):
        logpurged = False
        while not logpurged:
            try:
                os.remove(logfile)
                open(logfile, 'w').close()
                logpurged = True
            except PermissionError: # Someone is still holding the file, give it a sec
                sleep(1)
                pass
        os.startfile(PROCESS_NAME)  # Start MUGEN
        processloaded = False
        while not processloaded:
            try:
                self.p = self.rwm.get_process_by_name(PROCESS_NAME)
                self.p.open()
                processloaded = True
            except:
                print("Process not found! Is MUGEN running? Trying again...")
                sleep(2)
        self.win1_ptr = self.p.get_pointer(WIN_ADDRESS, [0x0000871C])
        self.win2_ptr = self.p.get_pointer(WIN_ADDRESS, [0x00008728])
        self.index = 0
        self.loadingchar = 2
        self.state = "loading"
    
    # Add a character to a list, returns True if success
    def add_character(self, charnum, pl):
        if(charnum < 0):
            return False
        if(pl == 1):
            self.player1_chars.append(charnum)
            return True
        elif(pl == 2):
            self.player2_chars.append(charnum)
            return True
        return False
    
    # returns the character queue for player pl
    def get_queue(self, pl):
        if(pl == 1):
            return self.player1_chars
        elif(pl == 2):
            return self.player2_chars
            
    # returns the character queue size for player pl
    def get_queue_size(self, pl):
        if(pl == 1):
            return len(self.player1_chars)
        elif(pl == 2):
            return len(self.player2_chars)

    # Read current match status from MUGEN's memory
    def readmem(self):
        self.p.read(WIN_ADDRESS)
        p1wins = int(self.p.read(self.p.get_pointer(WIN_ADDRESS, [0x0000871C])))
        p2wins = int(self.p.read(self.p.get_pointer(WIN_ADDRESS, [0x00008728])))
        self.debug("Match status: "+str(p1wins)+" - "+str(p2wins))
        if(p1wins == ROUNDS):
            self.winner = 1
        if(p2wins == ROUNDS):
            self.winner = 2


    # Scan the log file and do operations based on lines there
    def scanlines(self):        
        f = open(logfile,'r')           # Open logfile for reading
        lines = f.readlines()           # Read all lines to memory
        f.close()                       # Close the file for now   

        while(self.index < len(lines)):
            line = lines[self.index]
            self.index += 1
            
            # DETECT STATE CHANGES
            
            # Main menu loaded
            if(line.startswith("Mode select init")):
                self.state = "menu"
                continue

            # Character select loaded
            elif(line.startswith("Charsel init")):
                self.state = "charselect"
                continue
                
            # Fight
            elif(line.startswith("Game loop init")):
                self.state = "fight"
                continue
            
            
            # OTHER PROCESSING
            
            # Round / match ended, check scoreboard
            if(line.startswith("Finishing match") or line.startswith("Resetting round")):
                self.readmem()
                continue

            # Loading character
            if(line.startswith("Loading character")):
                self.loadingchar = int(self.loadingchar == 1) + 1 # Used for figuring out what failed, if any
                continue
                
            # Failed to load something
            if(line.endswith("failed to load\n") or line.endswith("failed to load")):
                # Character
                if(len(line.split("Character")) == 2):
                    self.winner = int(self.loadingchar==1)+1  # Mark the other player as winner
                    self.debug("ERROR: failed to load character for P"+str(self.loadingchar))
                    bchar = open(badcharfile,'a')
                    bchar.write(line)
                    bchar.close()
                # Something else
                else:
                    self.debug("UNHANDLED FAILURE TO LOAD")
                    self.debug(line)
                    self.winner = 0
                    
                # Kill mugen (if it is still alive showing error message)
                print("MUGEN failed, killing it!")
                os.kill(self.p.pid, signal.SIGTERM)
                self.reset() # reset everything
                return

    def debug(self, msg):
        global debug
        if(debug):
            print(msg)

    def select_char(self,charnum, player):
    # Player 1
        if(player == 1):
            char1_ptr = self.p.get_pointer(THREADSTACK0, [0x354 + 0x10]) # Get pointer to the char variable in memory
            self.press(OK,1) # Accept anything
            self.char1 = charnum
            if(not self.p.write(char1_ptr,charnum)): # Overwrite whatever was just accepted
                debug("Failed to write P1 character!")

    # Player 2
        else:
            char2_ptr = self.p.get_pointer(THREADSTACK0, [0x1E30 + 0x10]) # Get pointer to the char variable in memory
            self.press(OK,1) # Accept anything
            self.char2 = charnum
            if(not self.p.write(char2_ptr,charnum)): # Overwrite whatever was just accepted
                debug("Failed to write P2 character!")

    def press(self, button, times):
        for i in range(times):
            self.output_keyboard.press(button)
            sleep(HOLDTIME)
            self.output_keyboard.release(button)

    # Returns the number of winning player (1 or 2), -1 if no match has ended since last scan, 0 if draw (not sure when that would happen) 
    def scan(self):
        oldstate = self.state
        self.scanlines()
        if(oldstate != self.state):    # Has Game state changed?
            if(self.state == "menu"):
                self.press(OK,1)
            elif(self.state == "charselect"):
                if(len(self.player1_chars) > 0 and len(self.player2_chars) > 0):
                    self.press(OK,1) # TEAM MODE for P1 (single)
                    self.select_char(self.player1_chars.pop(0),1)
                    self.press(OK,1) # TEAM MODE for P2 (single)
                    self.select_char(self.player2_chars.pop(0),2)
                    self.press(OK,1) # STAGE SELECT (random)
                    
            elif(self.state == "fight"):
                pass    # Let 'em fight
        ret = self.winner
        self.winner = -1
        return ret
        
# FOR DEBUG PURPOSES
def main():
    operator = MugenOperator()
    p1 = [23,176,37,555]
    p2 = [14,67,234,987]
    win = -1
    print("STARTING")
    while(1):
        win = operator.scan()
        if(win == -1):
            pass
        if(win == 1):
            print("PLAYER 1 WON")
        if(win == 2):
            print("PLAYER 2 WON")
        if(win == 0):
            print("DRAW, HOW LAME")
            
        if(operator.get_queue_size(1) == 0 and len(p1) > 0):
            print(operator.add_character(p1.pop(0), 1))
        if(operator.get_queue_size(2) == 0 and len(p2) > 0):
            print(operator.add_character(p2.pop(0), 2))
        sleep(1)
if __name__ == "__main__":
    main()