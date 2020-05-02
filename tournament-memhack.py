from pynput.keyboard import Controller
from pynput.keyboard import Key
from time import sleep
from ReadWriteMemory import ReadWriteMemory

output_keyboard = Controller()
logfile = "mugen.log" # Path to log file to monitor

HOLDTIME = 0.1      # Time to hold r button
OK = "r"            # Button to press for selecting
NEXT = 'd'          # Button to press to move right
PREV = 'a'          # Button to press to move left
UP = 'w'            # Button to press to move up
DOWN = 's'          # Button to press to move down

ROUNDS = 2          # Rounds won required to win the match

state = "loading"   # what is currently happening in mugen
index = 0
player1_cursor = [0,0] # Current position of cursors
player2_cursor = [1,0]

player1_char = 0    # Character numbers for players
player2_char = 0

player1_next_char = [23,52,176,555]   # List of chars to load
player2_next_char = [87,35,97,945]

debug = True    # Enable debug prints

# Memory reader
rwm = ReadWriteMemory()
PROCESS_NAME = 'mugen.exe'
try:
    p = rwm.get_process_by_name(PROCESS_NAME)
    p.open()
except:
    print("Process not found! Is MUGEN running?")
    quit()
BASE_ADDRESS = 0x00400000
WIN_ADDRESS  = BASE_ADDRESS + 0x001040E8
win1_ptr = p.get_pointer(WIN_ADDRESS, [0x0000871C])
win2_ptr = p.get_pointer(WIN_ADDRESS, [0x00008728])
THREADSTACK0 = 0x0019FF7C - 0x418


def readmem():
    p.read(WIN_ADDRESS)
    p1wins = int(p.read(win1_ptr))
    p2wins = int(p.read(win2_ptr))
    debug("Match status: "+str(p1wins)+" - "+str(p2wins))
    if(p1wins == ROUNDS):
        print("P1 ("+str(player1_char)+") WINS")
        # DO SOMETHING HERE?
    if(p2wins == ROUNDS):
        print("P2 ("+str(player2_char)+") WINS")
        # DO SOMETHING HERE?


# Scan the log file and do operations based on lines there
def scanlines():
    global state
    global index
    global player1_char
    global player2_char
    global mem_processed
    
    f = open(logfile,'r')           # Open logfile for reading
    lines = f.readlines()           # Read all lines to memory
    f.close()                       # Close the file for now
    oldstate = state
    
    if(index == 0):
        index = len(lines)-1
        if(index < 0):
            index = 0
    
    # Log file renewed by mugen restart
    if(len(lines) < index - 1):
        index = len(lines)-1
        state = "loading"
    
    while(index < len(lines)):
        line = lines[index]
        index += 1
        
        # DETECT STATE CHANGES
        
        # Main menu loaded
        if(line.startswith("Mode select init")):
            state = "menu"
            player1_cursor = [0,0]  # Reset cursors
            player2_cursor = [1,0]
            continue

        # Character select loaded
        elif(line.startswith("Charsel init")):
            state = "charselect"
            continue
            
        # Fight
        elif(line.startswith("Game loop init")):
            state = "fight"
            continue
        
        
        # OTHER PROCESSING
                
        # Who won?
        if(line.startswith("Finishing match") or line.startswith("Resetting round")):
            readmem()
            
        
    # Return true if state changed
    if(state != oldstate):
        return True
    return False

def debug(msg):
    global debug
    if(debug):
        print(msg)

def select_char(charnum, player):
    global player1_char
    global player2_char
# Player 1
    if(player == 1):
        char1_ptr = p.get_pointer(THREADSTACK0, [0x354 + 0x10]) # Get pointer to the char variable in memory
        press(OK,1) # Accept anything
        player1_char = charnum
        if(not p.write(char1_ptr,charnum)): # Overwrite whatever was just accepted
            debug("Failed to write P2 character!")

# Player 2
    else:
        char2_ptr = p.get_pointer(THREADSTACK0, [0x1E30 + 0x10]) # Get pointer to the char variable in memory
        press(OK,1) # Accept anything
        player2_char = charnum
        if(not p.write(char2_ptr,charnum)): # Overwrite whatever was just accepted
            debug("Failed to write P2 character!")

def press(button, times):
    for i in range(times):
        output_keyboard.press(button)
        sleep(HOLDTIME)
        output_keyboard.release(button)

def main():
    waiting = False
    while(1):
        if(scanlines() or waiting):    # Has Game state changed?
            if(state == "menu"):
                waiting = False
                player1_cursor = [0,0]  # Reset cursors
                player2_cursor = [1,0]
                press(OK,1)
            elif(state == "charselect"):
                if(len(player1_next_char) > 0 and len(player2_next_char) > 0):
                    press(OK,1) # TEAM MODE for P1 (single)
                    select_char(player1_next_char.pop(0),1)
                    press(OK,1) # TEAM MODE for P2 (single)
                    select_char(player2_next_char.pop(0),2)
                    press(OK,1) # STAGE SELECT (random)
                    waiting = False
                else:
                    if not waiting: # So we only print this once
                        debug("Waiting for new fighters...")
                    waiting = True
                    
            elif(state == "fight"):
                waiting = False
                pass    # Let 'em fight
#        sleep(0.2)

if __name__ == "__main__":
    main()