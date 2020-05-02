import os

# The path to the select.def
selectfile = "data/db/select.def"

# The file to write character list to
charfile = "charlist.txt"

# Chars folder
charfolder = "chars"

# Include charcter path to the output
listcharpath = True

def main():
    f = open(selectfile,'r')
    lines = f.readlines()
    f.close()
    l = open(charfile,'w', encoding="utf8", errors="ignore")
    
    index = 0   # Index of next character found

    # Iterate select.def lines
    for line in lines:
        # Commented line
        if(line.strip().startswith(";")):
            continue
            
        # End of character list
        if(line.strip().startswith("[ExtraStages]")):
            break
        
        parts = line.split(",")[0].strip().split("/")
        
        # This is not an actual char line
        if(len(parts) < 3):
            continue
        
        charpath = charfolder
        for part in parts:
            charpath = os.path.join(charpath,part)
        if(not charpath.endswith(".def")):
            charpath = charpath + ".def"
        cf = open(charpath,'r', encoding="utf8", errors="replace")
        clines = cf.readlines()
        cf.close()
        charname = ""
        for cline in clines:
            if(cline.lower().strip().startswith("displayname") or (cline.lower().strip().startswith("name") and charname == "")):
                cparts = cline.split("=")
                charname = cparts[1].split('"')[1].strip()
        if(listcharpath):
            msg = str(index) + "," + str(charname)+","+str(charpath)+"\n"
        else:
            msg = str(index) + "," + str(charname)+"\n"
        l.write(msg)
        index += 1
    l.close()

if __name__ == "__main__":
    main()