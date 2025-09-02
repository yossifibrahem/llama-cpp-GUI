import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font
import subprocess
import threading
import os
import json
import webbrowser
try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

class ToolTip:
    """
    Creates a tooltip for a given widget.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip_window, text=self.text, justify='left',
            background='#ffffe0', relief='solid', borderwidth=1,
            font=("TkDefaultFont", 10)
        )
        label.pack(ipadx=5, ipady=5)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None

class LlamaServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LLaMA Server GUI Manager")
        self.root.geometry("800x700")
        self.root.minsize(800, 700)

        # Apply a modern theme
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Accent.TButton", foreground="white", background="#0078D7")

        # Server process management
        self.server_process = None
        self.is_running = False

        # System tray setup
        self.tray_icon = None
        self.is_in_tray = False

        # Configuration file path - use user's directory for portable executable
        self.config_file = self.get_config_path("llama_server_config.json")

        self.setup_ui()
        self.load_config()

    def get_config_path(self, filename):
        """Get the path for config file that works with PyInstaller"""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            # Use the directory where the executable is located
            app_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            app_dir = os.path.dirname(os.path.abspath(__file__))
        
        return os.path.join(app_dir, filename)

    def create_tray_icon(self):
        """Create a system tray icon"""
        if not TRAY_AVAILABLE:
            return None
        
        image = self.load_app_icon()
        
        # Create menu items
        menu_items = [
            item('Show Window', self.show_window),
            item('Open Browser', self.open_browser_from_tray, enabled=lambda item: self.is_running),
            pystray.Menu.SEPARATOR,
            item('Stop Server & Exit', self.quit_application),
        ]
        
        # Create the tray icon
        icon = pystray.Icon("llama_server", image, "LLaMA Server", menu=pystray.Menu(*menu_items))
        return icon

    def load_app_icon(self):
        """Load the app icon for system tray use"""
        try:
            # Try to load the same icon used for the window
            icon_path = resource_path("llama-cpp.ico")
            if os.path.exists(icon_path):
                # Load and resize the icon for tray use
                image = Image.open(icon_path)
                # Convert to RGBA if not already
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')
                # Resize to appropriate tray size (16x16 or 32x32)
                image = image.resize((32, 32), Image.Resampling.LANCZOS)
                return image
        except Exception as e:
            print(f"Could not load app icon for tray: {e}")
        
        return None

    def show_in_tray(self):
        """Minimize the application to system tray"""
        if not TRAY_AVAILABLE:
            messagebox.showwarning("System Tray", "System tray functionality requires 'pystray' and 'Pillow' packages.\nInstall them with: pip install pystray Pillow")
            return False
            
        self.root.withdraw()  # Hide the window
        self.is_in_tray = True
        
        if not self.tray_icon:
            self.tray_icon = self.create_tray_icon()
        
        # Run tray icon in a separate thread
        def run_tray():
            try:
                self.tray_icon.run()
            except Exception as e:
                print(f"Tray icon error: {e}")
        
        tray_thread = threading.Thread(target=run_tray, daemon=True)
        tray_thread.start()
        return True

    def show_window(self, icon=None, item=None):
        """Show the main window from tray"""
        self.is_in_tray = False
        self.root.deiconify()  # Show the window
        self.root.lift()  # Bring to front
        self.root.focus_force()
        
        # Stop the tray icon
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

    def open_browser_from_tray(self, icon=None, item=None):
        """Open browser from tray menu"""
        if self.is_running:
            self.open_browser()

    def quit_application(self, icon=None, item=None):
        """Stop server and quit the application"""
        if self.server_process and self.is_running:
            try:
                self.server_process.terminate()
            except Exception:
                pass
        
        if self.tray_icon:
            self.tray_icon.stop()
        
        # Use after_idle to ensure clean shutdown
        self.root.after_idle(self.root.quit)

    def setup_ui(self):
        """Sets up the main UI layout, including notebook and control buttons."""
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Create notebook for tabs
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill=tk.BOTH, expand=True)

        # --- Tab Frames ---
        main_frame = ttk.Frame(notebook, padding="10")
        tuning_frame = ttk.Frame(notebook, padding="10")
        features_frame = ttk.Frame(notebook, padding="10")
        output_frame = ttk.Frame(notebook, padding="10")

        notebook.add(main_frame, text="Main")
        notebook.add(tuning_frame, text="Tuning")
        notebook.add(features_frame, text="Features")
        notebook.add(output_frame, text="Server Output")

        self.setup_main_tab(main_frame)
        self.setup_tuning_tab(tuning_frame)
        self.setup_features_tab(features_frame)
        self.setup_output_tab(output_frame)

        # --- Control Buttons ---
        control_frame = ttk.Frame(main_container)
        control_frame.pack(fill=tk.X, pady=(10, 0))

        # Left-aligned buttons
        left_button_frame = ttk.Frame(control_frame)
        left_button_frame.pack(side=tk.LEFT)
        self.create_button(left_button_frame, "Save Config 💾", self.save_config, "Save the current settings to a JSON file.")
        self.create_button(left_button_frame, "Load Config 📂", self.load_config, "Load settings from the JSON configuration file.")
        self.create_button(left_button_frame, "Generate Command ⚡", self.show_command, "Show the final command that will be executed.")

        # Right-aligned buttons
        right_button_frame = ttk.Frame(control_frame)
        right_button_frame.pack(side=tk.RIGHT)
        self.browser_button = self.create_button(right_button_frame, "Open Browser 🌐", self.open_browser, "Open the web browser to access the server.", state=tk.DISABLED)
        self.stop_button = self.create_button(right_button_frame, "Stop Server ⏹️", self.stop_server, "Stop the currently running server process.", state=tk.DISABLED)
        self.start_button = self.create_button(right_button_frame, "Start Server ▶️", self.start_server, "Start the server with the current settings.", style="Accent.TButton")

    def setup_main_tab(self, parent):
        """Sets up the widgets in the 'Main' tab."""
        # --- Model Configuration ---
        model_group = ttk.Labelframe(parent, text="Model Configuration", padding="10")
        model_group.pack(fill=tk.X, pady=5)

        self.model_path = tk.StringVar()
        self.create_file_entry(model_group, "Model Path (-m):", self.model_path, "Path to the GGUF model file.", ".gguf", row=0)

        self.alias = tk.StringVar()
        self.create_entry(model_group, "Model Alias (-a):", self.alias, "Set an alias for the model, used in API calls.", row=1)

        # --- Multimodal ---
        mm_group = ttk.Labelframe(parent, text="Multimodal", padding="10")
        mm_group.pack(fill=tk.X, pady=5)
        self.mmproj_path = tk.StringVar()
        self.create_file_entry(mm_group, "Projector Path (--mmproj):", self.mmproj_path, "Path to a multimodal projector file. Optional if using a Hugging Face repo that includes one.", ".gguf", row=0)

        # --- Server Configuration ---
        server_group = ttk.Labelframe(parent, text="Server Configuration", padding="10")
        server_group.pack(fill=tk.X, pady=5)

        self.host = tk.StringVar(value="127.0.0.1")
        self.create_entry(server_group, "Host (--host):", self.host, "IP address to listen on (e.g., 0.0.0.0 for network access).", row=0)

        self.port = tk.StringVar(value="8080")
        self.create_entry(server_group, "Port (--port):", self.port, "The network port the server will listen on.", row=1)

        self.api_key = tk.StringVar()
        self.create_entry(server_group, "API Key (--api-key):", self.api_key, "API key for bearer token authentication (optional).", row=2)

    def setup_tuning_tab(self, parent):
        """Sets up the widgets in the 'Tuning' tab."""
        # --- Context & GPU ---
        context_group = ttk.Labelframe(parent, text="Context & GPU Offload", padding="10")
        context_group.pack(fill=tk.X, pady=5)

        self.ctx_size = tk.IntVar(value=4096)
        self.create_slider(context_group, "Context Size (-c):", self.ctx_size, "The context size (sequence length) for the model.",
                           from_=0, to=131072, resolution=1024, row=0)

        self.gpu_layers = tk.IntVar(value=99)
        self.create_slider(context_group, "GPU Layers (-ngl):", self.gpu_layers, "Number of model layers to offload to the GPU. 99 for all.",
                           from_=0, to=99, resolution=1, row=1)

        # --- Performance ---
        perf_group = ttk.Labelframe(parent, text="Performance", padding="10")
        perf_group.pack(fill=tk.X, pady=5)
        
        self.threads = tk.StringVar(value="")
        self.create_entry(perf_group, "Threads (-t):", self.threads, "Number of CPU threads to use (e.g., 8).", row=0)

        self.batch_size = tk.StringVar(value="")
        self.create_entry(perf_group, "Batch Size (-b):", self.batch_size, "Batch size for prompt processing (e.g., 2048).", row=1)
        
        self.parallel = tk.StringVar(value="")
        self.create_entry(perf_group, "Parallel Sequences (-np):", self.parallel, "Number of parallel sequences to process (e.g., 4).", row=2)

        # --- NEW PARAMETER ---
        self.moe_cpu_layers = tk.StringVar(value="")
        self.create_entry(perf_group, "MoE CPU Layers (--n-cpu-moe):", self.moe_cpu_layers, "Number of MoE layers to keep on the CPU. Used when the model doesn't fit on the GPU.", row=3)

        # --- Memory & Advanced Flags ---
        adv_flags_group = ttk.Labelframe(parent, text="Memory & Advanced Flags", padding="10")
        adv_flags_group.pack(fill=tk.X, pady=5)

        self.cont_batching = tk.BooleanVar(value=False)
        self.create_checkbutton(adv_flags_group, "Continuous Batching (-cb)", self.cont_batching, "Enable continuous batching for higher throughput.")

        self.flash_attn = tk.BooleanVar(value=False)
        self.create_checkbutton(adv_flags_group, "Flash Attention (-fa)", self.flash_attn, "Enable Flash Attention for faster processing.")

        self.mlock = tk.BooleanVar(value=False)
        self.create_checkbutton(adv_flags_group, "Memory Lock (--mlock)", self.mlock, "Lock the model in RAM to prevent swapping.")
        
        self.no_mmap = tk.BooleanVar(value=False)
        self.create_checkbutton(adv_flags_group, "No Memory Mapping (--no-mmap)", self.no_mmap, "Disable memory mapping of the model file.")

        self.numa = tk.BooleanVar(value=False)
        self.create_checkbutton(adv_flags_group, "NUMA Optimizations (--numa distribute)", self.numa, "Enable NUMA-aware optimizations.")

    def setup_features_tab(self, parent):
        """Sets up the widgets in the 'Features' tab."""
        # --- Chat Template ---
        chat_group = ttk.Labelframe(parent, text="Chat Template", padding="10")
        chat_group.pack(fill=tk.X, pady=5)

        self.chat_template = tk.StringVar()
        chat_templates = [
            "", "bailing", "chatglm3", "chatglm4", "chatml", "command-r", "deepseek", 
            "deepseek2", "deepseek3", "exaone3", "falcon3", "gemma", "gigachat", 
            "glmedge", "granite", "llama2", "llama2-sys", "llama2-sys-bos", 
            "llama2-sys-strip", "llama3", "llama4", "megrez", "minicpm", "mistral-v1", 
            "mistral-v3", "mistral-v3-tekken", "mistral-v7", "mistral-v7-tekken", 
            "monarch", "openchat", "orion", "phi3", "phi4", "rwkv-world", "smolvlm", 
            "vicuna", "vicuna-orca", "yandex", "zephyr"
        ]
        self.create_combobox(chat_group, "Template (--chat-template):", self.chat_template,
                             "Select a chat template. Leave blank for auto-detection from model.",
                             chat_templates, row=0)

        # --- LoRA ---
        lora_group = ttk.Labelframe(parent, text="LoRA Adapter", padding="10")
        lora_group.pack(fill=tk.X, pady=5)
        self.lora_path = tk.StringVar()
        self.create_file_entry(lora_group, "LoRA Path (--lora):", self.lora_path, "Path to a LoRA adapter file (optional).", ".gguf", row=0)

        # --- Speculative Decoding ---
        spec_group = ttk.Labelframe(parent, text="Speculative Decoding", padding="10")
        spec_group.pack(fill=tk.X, pady=5)
        
        self.draft_model_path = tk.StringVar()
        self.create_file_entry(spec_group, "Draft Model (-md):", self.draft_model_path, "Path to the draft model for speculative decoding.", ".gguf", row=0)
        self.draft_gpu_layers = tk.StringVar(value="")
        self.create_entry(spec_group, "Draft GPU Layers (-ngld):", self.draft_gpu_layers, "Number of layers to offload for the draft model.", row=1)
        self.draft_tokens = tk.StringVar(value="")
        self.create_entry(spec_group, "Draft Tokens (--draft):", self.draft_tokens, "Number of tokens to draft (e.g., 5).", row=2)

        # --- Other Flags ---
        flags_group = ttk.Labelframe(parent, text="Other Feature Flags", padding="10")
        flags_group.pack(fill=tk.X, pady=5)
        self.embedding = tk.BooleanVar(value=False)
        self.create_checkbutton(flags_group, "Embeddings Only (--embedding)", self.embedding, "Enable embedding-only mode.")
        self.jinja = tk.BooleanVar(value=False)
        self.create_checkbutton(flags_group, "Jinja (--jinja)", self.jinja, "Enable Jinja2 templating for chat (required for custom templates).")
        self.no_webui = tk.BooleanVar(value=False)
        self.create_checkbutton(flags_group, "Disable Web UI (--no-webui)", self.no_webui, "Disable the built-in web interface.")
        self.verbose = tk.BooleanVar(value=False)
        self.create_checkbutton(flags_group, "Verbose Logging (-v)", self.verbose, "Enable verbose server logging for debugging.")

        # --- Custom Arguments ---
        custom_group = ttk.Labelframe(parent, text="Custom Arguments", padding="10")
        custom_group.pack(fill=tk.X, expand=True, pady=5)
        self.custom_args = tk.StringVar()
        self.create_entry(custom_group, "Custom Arguments:", self.custom_args, "Enter any other command-line arguments, separated by spaces.", row=0)

    def setup_output_tab(self, parent):
        """Sets up the server output log view."""
        ttk.Label(parent, text="Server Log Output:").pack(anchor=tk.W, pady=(0, 5))
        monospace_font = font.Font(family="Consolas", size=10)
        self.output_text = scrolledtext.ScrolledText(parent, height=25, wrap=tk.WORD, font=monospace_font)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        clear_btn = ttk.Button(parent, text="Clear Output", command=self.clear_output)
        clear_btn.pack(pady=(10, 0), anchor=tk.E)
        ToolTip(clear_btn, "Clear all text from the log output window.")

    # --- UI Helper Methods ---
    def create_file_entry(self, parent, label_text, string_var, tooltip_text, file_ext, row):
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        file_path_frame = ttk.Frame(parent)
        file_path_frame.grid(row=row, column=1, sticky=tk.EW, pady=5)
        parent.columnconfigure(1, weight=1)
        entry = ttk.Entry(file_path_frame, textvariable=string_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        browse_btn = ttk.Button(file_path_frame, text="Browse", command=lambda: self.browse_file(string_var, file_ext))
        browse_btn.pack(side=tk.RIGHT)
        ToolTip(label, tooltip_text)
        ToolTip(entry, tooltip_text)
        ToolTip(browse_btn, f"Select a {file_ext} file.")

    def create_entry(self, parent, label_text, string_var, tooltip_text, row):
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        entry = ttk.Entry(parent, textvariable=string_var, width=30)
        entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        parent.columnconfigure(1, weight=1)
        ToolTip(label, tooltip_text)
        ToolTip(entry, tooltip_text)

    def create_combobox(self, parent, label_text, string_var, tooltip_text, values, row):
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        combobox = ttk.Combobox(parent, textvariable=string_var, values=values)
        combobox.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        parent.columnconfigure(1, weight=1)
        ToolTip(label, tooltip_text)
        ToolTip(combobox, tooltip_text)
        
    def create_slider(self, parent, label_text, int_var, tooltip_text, from_, to, resolution, row):
        slider_frame = ttk.Frame(parent)
        slider_frame.grid(row=row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        parent.columnconfigure(1, weight=1)
        label = ttk.Label(slider_frame, text=label_text)
        label.pack(anchor=tk.W)
        ToolTip(label, tooltip_text)
        control_frame = ttk.Frame(slider_frame)
        control_frame.pack(fill=tk.X, pady=(2, 0))
        slider = ttk.Scale(control_frame, from_=from_, to=to, orient=tk.HORIZONTAL,
                           variable=int_var, command=lambda v: self.update_slider_label(int_var, value_label, resolution))
        slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ToolTip(slider, tooltip_text)
        value_label = ttk.Label(control_frame, text=str(int_var.get()), width=8, anchor=tk.CENTER, relief=tk.SUNKEN)
        value_label.pack(side=tk.RIGHT)
        self.update_slider_label(int_var, value_label, resolution)

    def update_slider_label(self, int_var, label, resolution):
        raw_value = int_var.get()
        rounded_value = round(raw_value / resolution) * resolution
        int_var.set(rounded_value)
        label.config(text=str(rounded_value))

    def create_checkbutton(self, parent, text, variable, tooltip_text):
        cb = ttk.Checkbutton(parent, text=text, variable=variable)
        cb.pack(anchor=tk.W, padx=5, pady=2)
        ToolTip(cb, tooltip_text)

    def create_button(self, parent, text, command, tooltip_text, state=tk.NORMAL, style=None):
        kwargs = {'style': style} if style else {}
        btn = ttk.Button(parent, text=text, command=command, state=state, **kwargs)
        btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(btn, tooltip_text)
        return btn

    # --- Core Functionality ---
    def browse_file(self, string_var, file_ext):
        filename = filedialog.askopenfilename(
            title=f"Select {file_ext} File",
            filetypes=[(f"{file_ext.upper()} files", f"*{file_ext}"), ("All files", "*.*")]
        )
        if filename:
            string_var.set(filename)

    def generate_command(self):
        cmd = ["llama-server"] # Assuming 'server' executable is in the same directory
        
        if not self.model_path.get().strip():
            messagebox.showerror("Error", "Model path is required!")
            return None
        
        cmd.extend(["-m", self.model_path.get().strip()])
        
        # Add arguments from sliders/IntVar
        cmd.extend(['-c', str(self.ctx_size.get())])
        cmd.extend(['-ngl', str(self.gpu_layers.get())])
        
        # Add other string arguments if their values are not empty
        args = {
            '--host': self.host, '--port': self.port, '-a': self.alias,
            '--api-key': self.api_key, '-t': self.threads, '-b': self.batch_size, 
            '-np': self.parallel, '--lora': self.lora_path,
            '--mmproj': self.mmproj_path, '--chat-template': self.chat_template,
            '-md': self.draft_model_path, '-ngld': self.draft_gpu_layers,
            '--draft': self.draft_tokens, '--n-cpu-moe': self.moe_cpu_layers
        }
        for flag, var in args.items():
            if var.get().strip():
                cmd.extend([flag, var.get().strip()])
        
        # Boolean flags
        bool_args = {
            '-fa': self.flash_attn, '--no-mmap': self.no_mmap,
            '--no-webui': self.no_webui, '-cb': self.cont_batching,
            '--mlock': self.mlock, '--embedding': self.embedding,
            '--jinja': self.jinja, '-v': self.verbose
        }
        for flag, var in bool_args.items():
            if var.get():
                cmd.append(flag)

        if self.numa.get():
            cmd.extend(["--numa", "distribute"])
            
        if self.custom_args.get().strip():
            cmd.extend(self.custom_args.get().strip().split())
            
        return cmd

    def show_command(self):
        cmd = self.generate_command()
        if not cmd: return
        command_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in cmd)
        cmd_window = tk.Toplevel(self.root)
        cmd_window.title("Generated Command")
        cmd_window.geometry("600x200")
        ttk.Label(cmd_window, text="Generated Command:", padding="10 10 0 5").pack(anchor=tk.W)
        cmd_text = scrolledtext.ScrolledText(cmd_window, height=5, wrap=tk.WORD)
        cmd_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        cmd_text.insert(tk.END, command_str)
        cmd_text.config(state=tk.DISABLED)
        def copy_command():
            cmd_window.clipboard_clear()
            cmd_window.clipboard_append(command_str)
            messagebox.showinfo("Copied", "Command copied to clipboard!", parent=cmd_window)
        ttk.Button(cmd_window, text="Copy to Clipboard", command=copy_command).pack(pady=10)

    def start_server(self):
        if self.is_running: return
        cmd = self.generate_command()
        if not cmd: return
            
        self.output_text.delete(1.0, tk.END)
        command_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in cmd)
        self.update_output(f"▶ Starting server with command:\n{command_str}\n\n" + "="*80 + "\n")
        
        def run_server():
            try:
                # On Windows, prevent the console window from appearing
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                self.server_process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    universal_newlines=False, bufsize=1, startupinfo=startupinfo
                )
                
                for line_bytes in iter(self.server_process.stdout.readline, b''):
                    try:
                        line = line_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        line = line_bytes.decode('latin-1', errors='replace')
                    self.root.after(0, self.update_output, line)
                self.server_process.wait()
                self.root.after(0, self.server_stopped)
                
            except FileNotFoundError:
                self.root.after(0, self.update_output, f"\n⚠ Error: The 'llama-server' executable was not found. Make sure it's in the same directory as this script or in your system's PATH.\n")
                self.root.after(0, self.server_stopped)
            except Exception as e:
                self.root.after(0, self.update_output, f"\n⚠ Error starting server: {e}\n")
                self.root.after(0, self.server_stopped)
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.browser_button.config(state=tk.NORMAL)

    def stop_server(self):
        if self.server_process and self.is_running:
            try:
                self.server_process.terminate()
                self.update_output("\n" + "="*80 + "\n⏹️ Server stop requested...\n")
            except Exception as e:
                self.update_output(f"\n⚠ Error stopping server: {e}\n")

    def server_stopped(self):
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.browser_button.config(state=tk.DISABLED)
        self.update_output("⏹️ Server process has terminated.\n")

    def update_output(self, text):
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)

    def clear_output(self):
        self.output_text.delete(1.0, tk.END)

    def save_config(self):
        config = {
            # Main Tab
            'model_path': self.model_path.get(), 'alias': self.alias.get(),
            'host': self.host.get(), 'port': self.port.get(), 'api_key': self.api_key.get(),
            # Tuning Tab
            'ctx_size': self.ctx_size.get(), 'gpu_layers': self.gpu_layers.get(),
            'threads': self.threads.get(), 'batch_size': self.batch_size.get(),
            'parallel': self.parallel.get(), 'cont_batching': self.cont_batching.get(),
            'flash_attn': self.flash_attn.get(), 'mlock': self.mlock.get(),
            'no_mmap': self.no_mmap.get(), 'numa': self.numa.get(),
            'moe_cpu_layers': self.moe_cpu_layers.get(), # --- NEW PARAMETER ---
            # Features Tab
            'chat_template': self.chat_template.get(), 'lora_path': self.lora_path.get(),
            'mmproj_path': self.mmproj_path.get(),
            'draft_model_path': self.draft_model_path.get(), 
            'draft_gpu_layers': self.draft_gpu_layers.get(),
            'draft_tokens': self.draft_tokens.get(),
            'embedding': self.embedding.get(), 'jinja': self.jinja.get(),
            'no_webui': self.no_webui.get(), 'verbose': self.verbose.get(),
            'custom_args': self.custom_args.get()
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Success", f"Configuration saved to {self.config_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def load_config(self):
        if not os.path.exists(self.config_file): return
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            # Main Tab
            self.model_path.set(config.get('model_path', ''))
            self.alias.set(config.get('alias', ''))
            self.host.set(config.get('host', '127.0.0.1'))
            self.port.set(config.get('port', '8080'))
            self.api_key.set(config.get('api_key', ''))
            # Tuning Tab
            self.ctx_size.set(config.get('ctx_size', 4096))
            self.gpu_layers.set(config.get('gpu_layers', 99))
            self.threads.set(config.get('threads', ''))
            self.batch_size.set(config.get('batch_size', ''))
            self.parallel.set(config.get('parallel', ''))
            self.cont_batching.set(config.get('cont_batching', False))
            self.flash_attn.set(config.get('flash_attn', False))
            self.mlock.set(config.get('mlock', False))
            self.no_mmap.set(config.get('no_mmap', False))
            self.numa.set(config.get('numa', False))
            self.moe_cpu_layers.set(config.get('moe_cpu_layers', '')) # --- NEW PARAMETER ---
            # Features Tab
            self.chat_template.set(config.get('chat_template', ''))
            self.lora_path.set(config.get('lora_path', ''))
            self.mmproj_path.set(config.get('mmproj_path', ''))
            self.draft_model_path.set(config.get('draft_model_path', ''))
            self.draft_gpu_layers.set(config.get('draft_gpu_layers', ''))
            self.draft_tokens.set(config.get('draft_tokens', ''))
            self.embedding.set(config.get('embedding', False))
            self.jinja.set(config.get('jinja', False))
            self.no_webui.set(config.get('no_webui', False))
            self.verbose.set(config.get('verbose', False))
            self.custom_args.set(config.get('custom_args', ''))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {e}")

    def open_browser(self):
        """Opens the web browser at the server's address."""
        host = self.host.get().strip()
        if host == '0.0.0.0': host = 'localhost'
        url = f"http://{host}:{self.port.get().strip()}"
        try:
            webbrowser.open(url)
            self.update_output(f"🌐 Opened browser at {url}\n")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open browser: {e}")

def resource_path(filename):
    """Get absolute path to resource, works for dev and for PyInstaller bundle"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.join(sys._MEIPASS, filename)
    # Running as script
    return os.path.join(os.path.abspath("."), filename)

def main():
    root = tk.Tk()
    
    # Try to set icon - handle gracefully if it doesn't exist
    try:
        icon_path = resource_path("llama-cpp.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        # Icon not found or couldn't load - continue without it
        pass
    
    app = LlamaServerGUI(root)
    
    def on_closing():
        if not app.is_running:
            root.destroy()
            return

        response = messagebox.askyesnocancel(
            "Server Still Running",
            "The LLaMA server is active. Do you want to stop it before exiting?",
            detail="• Yes: Stop Server and Exit.\n"
                   "• No: Minimize to Tray\n"
                   "• Cancel: Return to Application",
            icon=messagebox.WARNING
        )
        if response is True:  # Yes - Stop server and exit
            app.stop_server()
            root.after(1000, root.destroy)
        elif response is False:  # No - Minimize to tray
            if app.show_in_tray():
                # Successfully minimized to tray
                pass
            else:
                # Tray not available, ask user what to do
                fallback = messagebox.askyesno(
                    "System Tray Unavailable",
                    "System tray functionality is not available.\n\n"
                    "Do you want to exit anyway and leave the server running?",
                    detail="The server process will continue running in the background.",
                    icon=messagebox.QUESTION
                )
                if fallback:
                    root.destroy()
        # If response is None (Cancel), do nothing and return to app
            
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Show warning if tray dependencies are missing
    if not TRAY_AVAILABLE:
        root.after(1000, lambda: messagebox.showinfo(
            "System Tray",
            "For full functionality including system tray support, install:\n\n"
            "pip install pystray Pillow\n\n"
            "This will allow the app to minimize to the system tray when a server is running.",
            icon=messagebox.INFO
        ))
    
    root.mainloop()

if __name__ == "__main__":
    main()