import tkinter as tk
from tkinter import scrolledtext, messagebox
from PIL import Image, ImageTk # type: ignore
import numpy as np # type: ignore
import sounddevice as sd; sd.default.latency = "low" # type: ignore
import keyboard # type: ignore
import time
import threading
import queue
import os
#import cProfile

Memory = []
Code = []
Cache = 0
MainCodeTemp=[]
MainIndexTemp=[]
MainMemoryTemp=[]
MainJmpTemp=[]
MainJmpCacheTemp=[]
Jmp = []
JmpCache = []
input_queue = queue.Queue()

def check_key(key):
    try:
        if keyboard.is_pressed(key):
            return 1
        else:
            return 0
    except ValueError as e:
        print (e)
        return -1

def makedir():
    directories = ['SAVE', 'FUNC']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)

def save_file(content: str) -> str:
    directory = os.path.join(os.getcwd(), "SAVE")
    base_filename = "save"
    index = 0
    while True:
        filename = f"{base_filename}{index}.txt"
        full_path = os.path.join(directory, filename)
        if not os.path.exists(full_path):
            with open(full_path, 'w') as file:
                file.write(content)
            return filename
        index += 1

def overwrite_file(content: str, index: int) -> str:
    directory = os.path.join(os.getcwd(), "SAVE")
    base_filename = "save"
    filename = f"{base_filename}{index}.txt"
    full_path = os.path.join(directory, filename)
    os.makedirs(directory, exist_ok=True)
    with open(full_path, 'w') as file:
        file.write(content)
    return filename

def delete_save(index):
    file_path = os.path.join("SAVE", f"save{index}.txt")
    if not os.path.exists(file_path):
        return 0 
    os.remove(file_path) 
    return 1

def interpret(c):
    c = c.upper()
    if c.strip() == "":
        return ["EMPTY", None]
    p = c.split()
    if p[0] == "COMMENT":
        return ["EMPTY", None]
    if (not(len(p) in [1, 2, 3])):
        return ["ERROR", "SYNTAX ERROR: A command should not have more than three objects."]
    if p[0] in ["OPENFILE","SAVEFILE","OVERSAVE","FUNCTION"]:
        if len(p)!=3:
            return["ERROR", "SYNTAX ERROR: File-related commands should have three objects."]
        try:
            p[2]=int(p[2])
        except ValueError as e:
            print (e)
            return ["ERROR", "SYNTAX ERROR: The assigned value should be an integer."]
        if p[2] < 0:
            return ["ERROR", "SYNTAX ERROR: The assigned value should be positive for a memory location."]
        if p[0] in ["SAVEFILE","OVERSAVE"]:
            try: p[1]=int(p[1])
            except ValueError as e:
                print (e)
                return ["ERROR", "SYNTAX ERROR: The assigned value should be an integer."]
            if p[1] < 0: return ["ERROR", "SYNTAX ERROR: The assigned value should be positive for a memory location."]
        return [p[0],[p[1],p[2]]]
    if p[0] == "UTIL":
        if len(p)!=3:
            if len(p)!=2:
                return ["ERROR", "SYNTAX ERROR: UTIL requires a utility identifier."]
            if p[1] == "STOPAUDIO":
                if len(p)!=2:
                    return ["ERROR", "SYNTAX ERROR: UTIL command for STOPAUDIO do not need a parameter."]
                return [p[1],None]
            return ["ERROR", "SYNTAX ERROR: UTIL commands for STRING, IMAGE and AUDIO should have three objects / one parameter"]
        if p[1] in ["STRING","IMAGE","AUDIO"]:
            try:
                p[2]=int(p[2])
            except ValueError as e:
                print (e)
                return ["ERROR", "SYNTAX ERROR: The assigned value should be an integer."]
            if p[2]<0:
                return ["ERROR", "SYNTAX ERROR: The assigned value should be positive for a memory location."]
            return [p[1],p[2]]
        elif p[1] == "KEY":
            return [p[1],p[2]]
        return ["ERROR","SYNTAX ERROR: No such command for UTIL."]
    if p[0] in ["LABEL", "ADD", "SUB", "JUMP", "BUMP+", "BUMP-", "JUMP0", "JUMP-", "ASSIGN", "READ", "WRITE", "DECLARE",
                "RNODE", "WNODE", "RETURN", "OPENSAVE", "MUL", "DIV", "MOD", "POWER", "WAIT"]:
        if len(p) != 2:
            return ["ERROR", "SYNTAX ERROR: This command requires one parameter / two objects."]
        if p[0] in ["ADD", "SUB", "BUMP+", "BUMP-", "ASSIGN", "READ", "WRITE", "DECLARE",
                    "RNODE", "WNODE", "RETURN", "OPENSAVE", "MUL", "DIV", "MOD", "POWER", "WAIT"]:
            try:
                p[1] = int(p[1])
                if p[0] in ["READ", "WRITE", "BUMP+", "BUMP-", "ADD", "SUB", "DECLARE",
                            "RNODE", "WNODE", "RETURN", "OPENSAVE", "MUL", "DIV", "MOD", "POWER"] and p[1] < 0:
                    return ["ERROR", "SYNTAX ERROR: The assigned value should be positive for a memory location."]
                return p
            except ValueError as e:
                print (e)
                return ["ERROR", "SYNTAX ERROR: The assigned value should be an integer."]
        elif p[0] in ["JUMP", "JUMP0", "JUMP-"]:
            if p[1] in Jmp:
                return p
            return ["ERROR", "SYNTAX ERROR: Did not find the label for the jump command."]
        elif p[0] == "LABEL":
            return p
        return p
    elif p[0] in ["INPUT", "OUTPUT", "EXIT", "DELSAVE"]:
        if len(p)!=1:
            return ["ERROR", "SYNTAX ERROR: Parameters are not needed"]
        return [c, None]
    return ["ERROR", "SYNTAX ERROR: Invalid command."]

def scanlabels(verbose):
    global Code, Jmp, JmpCache
    max_size = len(Code)
    Jmp = [None] * max_size
    JmpCache = [None] * max_size
    jmp_count = 0 
    for i in range(max_size):
        line = Code[i]
        if line.startswith("LABEL "):
            p = interpret(line)
            if p[1] not in Jmp[:jmp_count]: 
                Jmp[jmp_count] = p[1]
                JmpCache[jmp_count] = i
                jmp_count += 1
            else:
                return [False, i]
    Jmp = Jmp[:jmp_count]
    JmpCache = JmpCache[:jmp_count]
    return [True, 0]

audio_threads = {}

def play_sound(wavRate, wavRange, wavStereo, wavLEFT, wavRIGHT=None, stop_event=None):
    left_channel = np.clip(np.array(wavLEFT, dtype=np.int32), -wavRange, wavRange)
    if wavStereo and wavRIGHT is not None:
        right_channel = np.clip(np.array(wavRIGHT, dtype=np.int32), -wavRange, wavRange)
        audio_data = np.column_stack((left_channel, right_channel)).astype(np.float32) / wavRange
    else:
        audio_data = (left_channel.astype(np.float32) / wavRange)
    blocksize = 4
    with sd.OutputStream(samplerate=wavRate, channels=audio_data.shape[1], blocksize=blocksize) as stream:
        for start in range(0, audio_data.shape[0], blocksize):
            if stop_event is not None and stop_event.is_set():
                break
            end = start + blocksize
            stream.write(audio_data[start:end])

def play_audio(wavRate, wavRange, wavStereo, wavLEFT, wavRIGHT=None, label=None):
    stop_event = threading.Event()
    thread = threading.Thread(target=play_sound, args=(wavRate, wavRange, wavStereo, wavLEFT, wavRIGHT, stop_event))
    thread.start()
    if label is not None:
        if label not in audio_threads:
            audio_threads[label] = []
        audio_threads[label].append((thread, stop_event))

def stop_audio(label):
    if label in audio_threads:
        for thread, stop_event in audio_threads[label]:
            stop_event.set()
            thread.join()
        del audio_threads[label]
        return 1
    else:
        return 0

text = ""
text_box_window = None
image_window = None
image_label = None
colors = []

def update_image(width, height, color):
    threading.Thread(target=update_image_threaded, args=(width, height, color)).start() # type: ignore

def update_image(width, height, color):
    global image_window, image_label
    image = Image.new("RGB", (width, height))
    image.putdata([tuple(rgb) for rgb in color])
    if image_window is None:
        image_window = tk.Toplevel()
        image_window.title("Updated Image")
        image_label = tk.Label(image_window)
        image_label.pack()
        image_window.protocol("WM_DELETE_WINDOW", close_image)
    tk_image = ImageTk.PhotoImage(image)
    image_label.config(image=tk_image)
    image_label.image = tk_image
    image_window.geometry(f"{width}x{height}")
    if image_window.state() == "iconic":
        image_window.deiconify()
    else:
        image_window.lift()

def close_image():
    global image_window
    if image_window is not None:
        image_window.destroy()
        image_window = None

def update_text_box():
    global text_box_window, text
    if text_box_window is not None:
        text_box_window.lift()
        text_box_window.text_box.delete('1.0', tk.END)
        text_box_window.text_box.insert(tk.END, text)
    else:
        text_box_window = tk.Toplevel()
        text_box_window.title("Text Box")
        text_box_window.geometry("400x300")
        text_box_window.text_box = scrolledtext.ScrolledText(text_box_window, height=15)
        text_box_window.text_box.pack(fill=tk.BOTH, expand=True)
        text_box_window.text_box.insert(tk.END, text)
        text_box_window.protocol("WM_DELETE_WINDOW", close_text_box)

def close_text_box():
    global text_box_window
    if text_box_window is not None:
        text_box_window.destroy()
        text_box_window = None

inputting = False

def start(verbose, console_output, memory_output):
    global Code, Cache, Jmp, JmpCache, Memory, text, color, inputting
    global MainCodeTemp, MainIndexTemp, MainMemoryTemp, MainJmpTemp, MainJmpCacheTemp
    Cache = 0
    Jmp = []
    JmpCache = []
    Memory = []
    console_output.delete('1.0', tk.END)
    vLabels = scanlabels(verbose)
    if verbose:
        console_output.insert(tk.END, str(Jmp) + "\n" + str(JmpCache) + "\n")
        console_output.see(tk.END)
    if not vLabels[0]:
        console_output.insert(tk.END, f'in "{Code[vLabels[1]]}": SYNTAX ERROR: This label already exists.\n')
        console_output.see(tk.END)
        return False
    i = 0
    while True:
        if i >= len(Code):
            console_output.insert(tk.END, "PROGRAM ERROR: Attempting to execute beyond the end of code.\n")
            console_output.see(tk.END)
            return False
        line = Code[i]
        p = interpret(line)
        if verbose: 
            console_output.insert(tk.END, f"[{i}] {p}\n")
            console_output.see(tk.END)
        if p[0] == "EXIT":
            console_output.insert(tk.END, "The program has executed successfully.\n")
            console_output.see(tk.END)
            return True
        if p[0] == "ERROR":
            console_output.insert(tk.END, f'in "{i}", "{line}": {p[1]}\n')
            console_output.see(tk.END)
            return False
        if p[0] == "JUMP":
            try:
                Idx = Jmp.index(p[1])
                i = JmpCache[Idx]
                if verbose: 
                    console_output.insert(tk.END, f"[Jumps to: {i}]\n")
                    console_output.see(tk.END)
            except (ValueError, IndexError) as e:
                print (e)
                console_output.insert(tk.END, f'in "{i}", "{line}": PROGRAM ERROR: Did not find the label for the jump command.\n')
                console_output.see(tk.END)
                return False
        if p[0] == "JUMP0":
            if Cache == 0:
                try:
                    Idx = Jmp.index(p[1])
                    i = JmpCache[Idx]
                    if verbose: 
                        console_output.insert(tk.END, f"[Jumps to: {i}]\n")
                        console_output.see(tk.END)
                except (ValueError, IndexError) as e:
                    print (e)
                    console_output.insert(tk.END, f'in "{i}", "{line}": PROGRAM ERROR: Did not find the label for the jump command.\n')
                    console_output.see(tk.END)
                    return False
            else:
                i += 1
        if p[0] == "JUMP-":
            if Cache < 0:
                try:
                    Idx = Jmp.index(p[1])
                    i = JmpCache[Idx]
                    if verbose: 
                        console_output.insert(tk.END, f"[Jumps to: {i}]\n")
                        console_output.see(tk.END)
                except (ValueError, IndexError) as e:
                    print (e)
                    console_output.insert(tk.END, f'in "{i}", "{line}": PROGRAM ERROR: Did not find the label for the jump command.\n')
                    console_output.see(tk.END)
                    return False
            else:
                i += 1
        if p[0] == "ASSIGN":
            Cache = p[1]
        if p[0] == "WAIT":
            if p[1]>=0:
                time.sleep(p[1]/1000)
            else:
                console_output.insert(tk.END, f'in "{i}", "{line}": SYNTAX ERROR: Negative values are invalid for waiting.\n')
                console_output.see(tk.END)
                return False
        if p[0] == "INPUT":
            console_output.insert(tk.END, "Waiting for user input...\n")
            console_output.see(tk.END)
            inputting = True
            while True:
                try:
                    user_input = input_queue.get(timeout=1)
                    Cache = int(user_input)
                    console_output.insert(tk.END, f"INPUT: {Cache}\n")
                    console_output.see(tk.END)
                    break
                except queue.Empty as e:
                    print (e)
                    continue
                except ValueError as e:
                    print (e)
                    console_output.insert(tk.END, f'in input "{user_input}": ')
                    console_output.insert(tk.END, "INPUT ERROR: Please enter a valid integer.\n")
                    console_output.see(tk.END)
            inputting = False
        if p[0] == "OUTPUT":
            console_output.insert(tk.END, f"OUTPUT: {Cache}\n")
            console_output.see(tk.END)
        if p[0] == "DECLARE":
            if p[1] > len(Memory):
                Memory.extend([0] * (p[1] - len(Memory)))
            elif p[1] < len(Memory):
                Memory = Memory[:p[1]]
        try:
            if p[0] == "STRING":
                text = ""
                if Memory[p[1]] <= 0:
                    console_output.insert(tk.END, f'in "{i}", "{line}": SYNTAX ERROR: A piece of STRING should not have an empty or negative length.\n')
                    console_output.see(tk.END)
                    return False
                for strIndex in range(1, Memory[p[1]] + 1): 
                    try:
                        char_value = Memory[p[1] + strIndex]
                        if char_value < 0 or char_value > 0x10FFFF:
                            raise ValueError(f"Value {char_value} is not in range for Unicode.")
                        text += chr(char_value)
                    except ValueError as ve:
                        print (ve)
                        console_output.insert(tk.END, f'in "{i}", "{line}": VALUE ERROR: Other errors related to unicode have occured.\n')
                        console_output.see(tk.END)
                        return False
                update_text_box()
            if p[0] == "IMAGE":
                color = []
                if Memory[p[1]] <= 0 or Memory[p[1]+1] <= 0:
                    console_output.insert(tk.END, f'in "{i}", "{line}": VALUE ERROR: Length or Width should not be empty or negative.\n')
                    console_output.see(tk.END)
                    return False
                imgLength = Memory[p[1]]
                imgWidth = Memory[p[1]+1]
                imgStart = p[1]+2
                color = [[(Memory[imgStart + imgIndex * 3])% 256,
                          (Memory[imgStart + imgIndex * 3 + 1])% 256,
                          (Memory[imgStart + imgIndex * 3 + 2])% 256]
                         for imgIndex in range(imgLength * imgWidth)]
                update_image(imgWidth, imgLength, color)
            if p[0] == "AUDIO":
                auxLength, auxRate, auxRange, auxStereo = Memory[p[1]:p[1]+4]
                if auxLength <= 0 or auxRate <= 0 or auxRange <= 0:
                    console_output.insert(tk.END, f'in "{i}", "{line}": VALUE ERROR: Audio parameters should not be empty or negative.\n')
                    console_output.see(tk.END)
                    return False
                auxStart = p[1]+4
                auxLEFT=[]
                auxRIGHT=[]
                auxLEFT=Memory[auxStart:auxStart+auxLength]
                if auxStereo > 0:
                    auxStereo = True
                    auxStart = auxStart+auxLength
                    auxRIGHT=Memory[auxStart:auxStart+auxLength]
                else:
                    auxStereo = False
                    auxRIGHT = None
                play_audio(auxRate,auxRange,auxStereo,auxLEFT,auxRIGHT,Cache)
            if p[0] == "STOPAUDIO":
                stop_audio(label = Cache)
            if p[0] == "KEY":
                Cache = check_key(p[1])
                if Cache == -1:
                    console_output.insert(tk.END, f'in "{i}", "{line}": SYNTAX ERROR: The key does not exist.\n')
                    console_output.see(tk.END)
                    return False
            if p[0] == "READ":
                Cache = Memory[p[1]]
            if p[0] == "WRITE":
                Memory[p[1]] = Cache
            if p[0] == "ADD":
                Cache += Memory[p[1]]
            if p[0] == "SUB":
                Cache -= Memory[p[1]]
            if p[0] == "MUL":
                Cache *= Memory[p[1]]
            if p[0] == "DIV":
                Cache = int(Cache / Memory[p[1]])
            if p[0] == "MOD":
                Cache = Cache % Memory[p[1]]
            if p[0] == "POWER":
                Cache = int(Cache**Memory[p[1]])
            if p[0] == "BUMP+":
                Memory[p[1]] += 1
            if p[0] == "BUMP-":
                Memory[p[1]] -= 1
            if p[0] == "RNODE":
                if Memory[Memory[p[1]]]<0:
                    console_output.insert(tk.END, f'in "{i}", "{line}": VALUE ERROR: A memory location should not be negative.\n')
                    console_output.see(tk.END)
                    return False
                Cache = Memory[Memory[p[1]]]
            if p[0] == "WNODE":
                if Memory[Memory[p[1]]]<0:
                    console_output.insert(tk.END, f'in "{i}", "{line}": VALUE ERROR: A memory location should not be negative.\n')
                    console_output.see(tk.END)
                    return False
                Memory[Memory[p[1]]] = Cache
        except (IndexError, ValueError) as e:
            print (e)
            console_output.insert(tk.END, f'in "{i}", "{line}": VALUE ERROR: You did not declare enough memory for this operation.\n')
            console_output.see(tk.END)
            return False
        try:
            if p[0] == "OPENSAVE":
                if Cache<0:
                    console_output.insert(tk.END, f'in "{i}", "{line}": VALUE ERROR: Cache should not be negative for save files.\n')
                    console_output.see(tk.END)
                    return False
                if not (os.path.exists(os.path.join("SAVE", f"save{Cache}.txt"))):
                    console_output.insert(tk.END, f'in "{i}", "{line}": FILE ERROR: Did not find the file you were looking for.\n')
                    console_output.see(tk.END)
                    return False
                with open(os.path.join("SAVE", f"save{Cache}.txt")) as f:
                    fileInfo = list(map(int, f.read().split()))
                fileStart = p[1]
                fileIndex = 0
                Memory[fileStart:fileStart+len(fileInfo)] = fileInfo
            if p[0] == "OPENFILE":
                filename = p[1][0]
                if not (os.path.exists(os.path.join("SAVE", f"{filename}.txt"))):
                    console_output.insert(tk.END, f'in "{i}", "{line}": FILE ERROR: Did not find the file you were looking for.\n')
                    console_output.see(tk.END)
                    return False
                with open(os.path.join("SAVE", f"{filename}.txt")) as f:
                    fileInfo = list(map(int, f.read().split()))
                fileStart = p[1][1]
                fileIndex = 0
                Memory[fileStart:fileStart+len(fileInfo)] = fileInfo
            if p[0] == "SAVEFILE":
                fileStart = p[1][0]
                fileEnd = p[1][1]
                if fileStart >= fileEnd:
                    console_output.insert(tk.END, f'in "{i}", "{line}": VALUE ERROR: Starting value should not be larger than Ending value.\n')
                    console_output.see(tk.END)
                    return False
                memList = Memory[fileStart:fileEnd+1]
                combined_string = ' '.join(map(str, memList))
                save_file(combined_string)
            if p[0] == "OVERSAVE":
                fileStart = p[1][0]
                fileEnd = p[1][1]
                if fileStart >= fileEnd:
                    console_output.insert(tk.END, f'in "{i}", "{line}": VALUE ERROR: Starting value should not be larger than Ending value.\n')
                    console_output.see(tk.END)
                    return False
                memList = Memory[fileStart:fileEnd+1]
                combined_string = ' '.join(map(str, memList))
                if Cache<0:
                    console_output.insert(tk.END, f'in "{i}", "{line}": VALUE ERROR: Cache should not be negative for save files.\n')
                    console_output.see(tk.END)
                    return False
                overwrite_file(combined_string, Cache)
            if p[0] == "DELSAVE":
                if Cache<0:
                    console_output.insert(tk.END, f'in "{i}", "{line}": VALUE ERROR: Cache should not be negative for save files.\n')
                    console_output.see(tk.END)
                    return False
                delete_save(Cache)
            if p[0] == "FUNCTION":
                filename = p[1][0]
                file_path = os.path.join("FUNC", f"{filename}.txt")
                if not os.path.exists(file_path):
                    console_output.insert(tk.END, f'in "{i}", "{line}": FILE ERROR: Did not find the FUNCTION file you were looking for.\n')
                    console_output.see(tk.END)
                    return False
                MainIndexTemp.append(i)
                MainCodeTemp.append(Code)
                MainMemoryTemp.append(Memory)
                MainJmpTemp.append(Jmp)
                MainJmpCacheTemp.append(JmpCache)
                Code = []
                try:
                    with open(file_path,"r") as func_file:
                        Code.extend(func_file.read().splitlines())
                except Exception as e:
                    print (e)
                    console_output.insert(tk.END, f'in "{i}", "{line}": FILE ERROR: Unable to read the file.\n')
                    console_output.see(tk.END)
                    return False
                if Memory[p[1][1]] < 0:
                    console_output.insert(tk.END, f'in "{i}", "{line}": VALUE ERROR: You should not have a negative continuation.\n')
                    console_output.see(tk.END)
                    return False
                funLen=Memory[p[1][1]]
                funStart = p[1][1]+1
                if funLen == 0:
                    Memory = []
                else:
                    Memory = MainMemoryTemp[-1][funStart:funStart + funLen]
                i=0
                Jmp=[]
                JmpCache=[]
                vLabels = scanlabels(verbose)
                if not vLabels[0]:
                    console_output.insert(tk.END, f'in "{Code[vLabels[1]]}": SYNTAX ERROR: This label already exists.\n')
                    console_output.see(tk.END)
                    return False
            if p[0] == "RETURN":
                if len(MainIndexTemp) == 0:
                    console_output.insert(tk.END, f'in "{i}", "{line}": SYNTAX ERROR: You should not return in the main code.\n')
                    console_output.see(tk.END)
                    return False
                if Memory[p[1]] < 0:
                    console_output.insert(tk.END, f'in "{i}", "{line}": VALUE ERROR: A memory location should not be negative.\n')
                    console_output.see(tk.END)
                    return False
                returnpos = Memory[p[1]]
                returnvalue = Memory
                i = MainIndexTemp.pop()
                Code = MainCodeTemp.pop()
                Memory = MainMemoryTemp.pop()
                Jmp = MainJmpTemp.pop()
                JmpCache = MainJmpCacheTemp.pop()
                if len(returnvalue)!=0:
                    Memory[returnpos:returnpos+len(returnvalue)] = returnvalue
        except (IndexError, ValueError) as e:
            console_output.insert(tk.END, f'in "{i}", "{line}": VALUE ERROR: You did not declare enough memory for this operation.\n')
            print (e)
            console_output.see(tk.END)
            return False
        memory_output.config(state='normal')
        memory_output.delete('1.0', tk.END)
        memory_output.insert(tk.END, ("Cache: " + str(Cache) + "\n") + ("Memory: " + str(Memory)[:64] + "\n"))
        memory_output.config(state='disabled')
        if not("JUMP" in p[0]) and p[0]!="FUNCTION":
            i += 1

class InterpreterApp:
    def __init__(self, master):
        self.master = master
        master.title("CAIE Pseudocode Sucks!!!")
        master.geometry("600x800")
        bg_color = "#333333"
        fg_color = "#FFFFFF"
        console_bg = "#000000"
        button_bg = "#555555"
        master.configure(bg=bg_color)
        self.code_frame = tk.Frame(master, bg=bg_color)
        self.code_frame.pack(fill='both', expand=True)
        self.code_label = tk.Label(self.code_frame, text="Enter Code:", bg=bg_color, fg=fg_color)
        self.code_label.pack(anchor='nw')
        self.code_input = scrolledtext.ScrolledText(self.code_frame, height=15, bg=console_bg, fg=fg_color, insertbackground=fg_color)
        self.code_input.pack(fill='both', expand=True)
        self.console_frame = tk.Frame(master, bg=bg_color)
        self.console_frame.pack(fill='x')
        self.console_label = tk.Label(self.console_frame, text="Console Output:", bg=bg_color, fg=fg_color)
        self.console_label.pack(anchor='nw')
        self.console_output = scrolledtext.ScrolledText(self.console_frame, height=10, bg=console_bg, fg=fg_color, state='disabled', insertbackground=fg_color)
        self.console_output.pack(fill='x', expand=True)
        self.memory_label = tk.Label(self.console_frame, text="Memory:", bg=bg_color, fg=fg_color)
        self.memory_label.pack(anchor='nw')
        self.memory_output = scrolledtext.ScrolledText(self.console_frame, height=5, bg=console_bg, fg=fg_color, state='disabled', insertbackground=fg_color)
        self.memory_output.pack(fill='x', expand=True)
        self.verbose_var = tk.BooleanVar()
        self.verbose_checkbox = tk.Checkbutton(master, text="Verbose Mode", variable=self.verbose_var, bg=bg_color, fg=fg_color, selectcolor=bg_color)
        self.verbose_checkbox.pack()
        self.run_button = tk.Button(master, text="Run", command=self.run_code, bg=button_bg, fg=fg_color)
        self.run_button.pack()
        self.input_label = tk.Label(master, text="Input:  ", bg=bg_color, fg=fg_color)
        self.input_label.pack()
        self.input_field = tk.Entry(master, bg=console_bg, fg=fg_color, insertbackground=fg_color)
        self.input_field.pack()
        self.input_button = tk.Button(master, text="Submit Input", command=self.submit_input, bg=button_bg, fg=fg_color, state='disabled')
        self.input_button.pack()
        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=1)
        # self.input_field.bind("<KeyRelease>", self.check_input)
        self.input_button.config(state='disabled')
        self.check_thread = threading.Thread(target=self.check_input_continuously)
        self.check_thread.daemon = True
        self.check_thread.start()

    def check_input(self):
        if self.input_field.get().strip() == "" or not inputting:
            self.input_button.config(state='disabled')
        else:
            self.input_button.config(state='normal')

    def run_code(self):
        self.run_button.config(state='disabled')
        self.verbose_checkbox.config(state='disabled')
        code = self.code_input.get("1.0", tk.END)
        Code.clear()
        Code.extend(line for line in code.splitlines() if line.strip())
        self.console_output.config(state='normal')
        self.memory_output.config(state='normal')
        self.memory_output.delete('1.0', tk.END)
        self.memory_output.config(state='disabled')
        threading.Thread(target=self.start_interpreter, daemon=True).start()

    def start_interpreter(self):
        verbose = self.verbose_var.get()
        makedir()
        start(verbose, self.console_output, self.memory_output)
        close_text_box()
        close_image()
        self.run_button.config(state='normal')
        self.verbose_checkbox.config(state='normal')

    def check_input_continuously(self):
        try:
            while True:
                self.check_input()
                time.sleep(0.01)
        except Exception as e:
            print (e)
            print ("Program closed.")

    def submit_input(self):
        user_input = self.input_field.get()
        if user_input.strip():
            input_queue.put(user_input)
            self.input_field.delete(0, tk.END)
        inputting = False

if __name__ == "__main__":
    root = tk.Tk()
    app = InterpreterApp(root)
    root.mainloop()
    
