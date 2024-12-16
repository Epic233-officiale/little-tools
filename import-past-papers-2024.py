import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import ImageGrab, Image
import json
import os
import threading

PICTURE_DIR = "Pictures"

if not os.path.exists(PICTURE_DIR):
    os.makedirs(PICTURE_DIR)

class QuestionInputApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Question Input System")
        self.last_subject = None
        self.last_subtype = None
        self.last_type = None

        self.init_gui()

    def init_gui(self):
        self.subject_label = tk.Label(self.root, text="Enter Subject (e.g., Physics):")
        self.subject_label.grid(row=0, column=0, sticky="w")
        self.subject_entry = tk.Entry(self.root)
        self.subject_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.subtype_label = tk.Label(self.root, text="Enter Subtype (e.g., Particle Physics):")
        self.subtype_label.grid(row=1, column=0, sticky="w")
        self.subtype_entry = tk.Entry(self.root)
        self.subtype_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.type_label = tk.Label(self.root, text="Enter Question Type (MCQ, SQ, LA):")
        self.type_label.grid(row=2, column=0, sticky="w")
        self.type_entry = tk.Entry(self.root)
        self.type_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.question_label = tk.Label(self.root, text="Enter Question (multiple lines):")
        self.question_label.grid(row=3, column=0, sticky="w")
        self.question_text = tk.Text(self.root, height=10, wrap=tk.WORD)
        self.question_text.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.graph_label = tk.Label(self.root, text="Does the question require a graph?")
        self.graph_label.grid(row=4, column=0, sticky="w")
        self.graph_choice = ttk.Combobox(self.root, values=["No", "Yes"])
        self.graph_choice.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        self.graph_choice.set("No")
        self.graph_button = tk.Button(self.root, text="Update/Import", command=self.choose_graph)
        self.graph_button.grid(row=5, column=0, columnspan=2, pady=10)
        self.image_path = None
        self.image_label = tk.Label(self.root, text="No image selected.")
        self.image_label.grid(row=6, column=0, columnspan=2)
        self.criteria_label = tk.Label(self.root, text="Enter Marking Criteria:")
        self.criteria_label.grid(row=7, column=0, sticky="w")
        self.criteria_text = tk.Text(self.root, height=8, wrap=tk.WORD)
        self.criteria_text.grid(row=7, column=1, padx=5, pady=5, sticky="ew")
        self.max_marks_label = tk.Label(self.root, text="Enter Maximum Marks:")
        self.max_marks_label.grid(row=8, column=0, sticky="w")
        self.max_marks_entry = tk.Entry(self.root)
        self.max_marks_entry.grid(row=8, column=1, padx=5, pady=5)
        self.save_button = tk.Button(self.root, text="Save Question", command=self.save_question)
        self.save_button.grid(row=9, column=0, columnspan=2, pady=10)

    def choose_graph(self):
        graph_choice = self.graph_choice.get().lower()
        if graph_choice == "yes":
            choice = messagebox.askyesno("Select Image", "Do you want to choose the image from clipboard?")
            if choice:
                self.get_image_from_clipboard()
            else:
                self.get_image_from_file()
        else:
            self.image_path = None
            self.image_label.config(text="No image selected.")

    def get_image_from_clipboard(self):
        try:
            image = ImageGrab.grabclipboard()
            if image:
                filename = self.get_available_image_filename()
                image.save(os.path.join(PICTURE_DIR, filename))
                self.image_path = os.path.join(PICTURE_DIR, filename)
                self.image_label.config(text=f"Image saved as {filename}")
            else:
                messagebox.showerror("No Image", "No image found in clipboard.")
        except Exception as e:
            messagebox.showerror("Error", f"Error while grabbing clipboard image: {e}")

    def get_image_from_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif")])
        if file_path:
            self.image_path = file_path
            self.image_label.config(text=f"Selected image: {os.path.basename(file_path)}")

    def get_available_image_filename(self):
        existing_files = os.listdir(PICTURE_DIR)
        existing_numbers = [int(f.split('.')[0]) for f in existing_files if f.endswith('.png')]
        next_number = max(existing_numbers, default=-1) + 1
        return f"{next_number}.png"

    def save_question(self):
        """ Save the entered question to a JSON file """
        subject = self.subject_entry.get().strip()
        subtype = self.subtype_entry.get().strip()
        question_type = self.type_entry.get().strip().lower()
        question = self.question_text.get("1.0", "end-1c").strip()
        marking_criteria = self.criteria_text.get("1.0", "end-1c").strip()
        try:
            max_marks = int(self.max_marks_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number for maximum marks.")
            return
        
        if not subject or not subtype or not question_type or not question or not marking_criteria or not max_marks:
            messagebox.showerror("Missing Information", "All fields are required.")
            return
        graph_filename = os.path.basename(self.image_path) if self.image_path else None
        question_data = [{
            "question": question,
            "graph_filename": graph_filename,
            "maximum_marks": max_marks,
            "marking_criteria": marking_criteria.split("\n"),
            "subject": subject,
            "subtype": subtype,
            "question_type": question_type
        }]
        self.save_to_json(question_data)

    def save_to_json(self, data, filename="questions_data.json"):
        if os.path.exists(filename):
            try:
                with open(filename, "r") as file:
                    all_data = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                all_data = []
        else:
            all_data = []

        all_data.extend(data)

        with open(filename, "w") as file:
            json.dump(all_data, file, indent=4)

        messagebox.showinfo("Success", "Data successfully saved.")

def main():
    root = tk.Tk()
    app = QuestionInputApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
