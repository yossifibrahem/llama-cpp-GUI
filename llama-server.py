import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font
import subprocess
import threading
import os
import json
import webbrowser 

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
        self.root.geometry("800x600")
        self.root.minsize(800, 600)

        # Apply a modern theme
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Accent.TButton", foreground="white", background="#0078D7")

        # Server process management
        self.server_process = None
        self.is_running = False
        
        # Configuration file path
        self.config_file = "llama_server_config.json"
        
        self.setup_ui()
        self.load_config()
        
    def setup_ui(self):
        """Sets up the main UI layout, including notebook and control buttons."""
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Create notebook for tabs
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # --- Tab Frames ---
        main_frame = ttk.Frame(notebook, padding="10")
        advanced_frame = ttk.Frame(notebook, padding="10")
        output_frame = ttk.Frame(notebook, padding="10")

        notebook.add(main_frame, text="Main Parameters")
        notebook.add(advanced_frame, text="Advanced")
        notebook.add(output_frame, text="Server Output")
        
        self.setup_main_tab(main_frame)
        self.setup_advanced_tab(advanced_frame)
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
        """Sets up the widgets in the 'Main Parameters' tab."""
        # --- Model & Context ---
        model_group = ttk.Labelframe(parent, text="Model & Context", padding="10")
        model_group.pack(fill=tk.X, pady=5)
        
        # Model Path
        ttk.Label(model_group, text="Model Path (.gguf):").grid(row=0, column=0, sticky=tk.W, pady=5)
        model_path_frame = ttk.Frame(model_group)
        model_path_frame.grid(row=0, column=1, sticky=tk.EW, pady=5)
        model_group.columnconfigure(1, weight=1)
        self.model_path = tk.StringVar()
        model_entry = ttk.Entry(model_path_frame, textvariable=self.model_path)
        model_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ToolTip(model_entry, "Path to the GGUF model file you want to serve.")
        browse_btn = ttk.Button(model_path_frame, text="Browse", command=self.browse_model)
        browse_btn.pack(side=tk.RIGHT)
        ToolTip(browse_btn, "Open a file dialog to select a .gguf model.")

        # Context Size Slider
        self.ctx_size = tk.IntVar(value=4096)
        self.create_slider(model_group, "Context Size (-c):", self.ctx_size, "The context size (sequence length) for the model.", 
                          from_=0, to=131072, resolution=1024, row=1)

        # GPU Layers Slider
        self.gpu_layers = tk.IntVar(value=99)
        self.create_slider(model_group, "GPU Layers (-ngl):", self.gpu_layers, "Number of model layers to offload to the GPU. 99 for all.", 
                          from_=0, to=99, resolution=1, row=2)

        # --- Server Configuration ---
        server_group = ttk.Labelframe(parent, text="Server Configuration", padding="10")
        server_group.pack(fill=tk.X, pady=5)
        
        self.port = tk.StringVar(value="8080")
        self.create_entry(server_group, "Port (--port):", self.port, "The network port the server will listen on.", row=0)
        
        # --- Common Flags ---
        flags_group = ttk.Labelframe(parent, text="Common Flags", padding="10")
        flags_group.pack(fill=tk.X, pady=5)

        self.jinja = tk.BooleanVar(value=True)
        self.create_checkbutton(flags_group, "Jinja (--jinja)", self.jinja, "Enable Jinja2 templating for chat.")
        
        self.flash_attn = tk.BooleanVar(value=False)
        self.create_checkbutton(flags_group, "Flash Attention (-fa)", self.flash_attn, "Enable Flash Attention for faster processing.")

        self.no_mmap = tk.BooleanVar(value=False)
        self.create_checkbutton(flags_group, "No Memory Mapping (--no-mmap)", self.no_mmap, "Disable memory mapping of the model file.")
        
        self.no_webui = tk.BooleanVar(value=False)
        self.create_checkbutton(flags_group, "Disable Web UI (--no-webui)", self.no_webui, "Disable the built-in web interface.")
  

    def setup_advanced_tab(self, parent):
        """Sets up the widgets in the 'Advanced' tab."""
        # --- Performance Tuning ---
        perf_group = ttk.Labelframe(parent, text="Performance Tuning", padding="10")
        perf_group.pack(fill=tk.X, pady=5)
        
        self.threads = tk.StringVar(value="")
        self.create_entry(perf_group, "Threads (-t):", self.threads, "Number of CPU threads to use (e.g., 8).", row=0)

        self.batch_size = tk.StringVar(value="")
        self.create_entry(perf_group, "Batch Size (-b):", self.batch_size, "Batch size for prompt processing (e.g., 512).", row=1)
        
        self.parallel = tk.StringVar(value="")
        self.create_entry(perf_group, "Parallel Sequences (-np):", self.parallel, "Number of parallel sequences to process (e.g., 4).", row=2)

        # --- Advanced Flags ---
        adv_flags_group = ttk.Labelframe(parent, text="Advanced Flags", padding="10")
        adv_flags_group.pack(fill=tk.X, pady=5)

        self.cont_batching = tk.BooleanVar(value=True)
        self.create_checkbutton(adv_flags_group, "Continuous Batching (-cb)", self.cont_batching, "Enable continuous batching for higher throughput.")

        self.mlock = tk.BooleanVar(value=False)
        self.create_checkbutton(adv_flags_group, "Memory Lock (--mlock)", self.mlock, "Lock the model in RAM to prevent swapping.")
        
        self.numa = tk.BooleanVar(value=False)
        self.create_checkbutton(adv_flags_group, "NUMA Optimizations (--numa distribute)", self.numa, "Enable NUMA-aware optimizations.")

        # --- Mixture of Experts (MoE) ---
        moe_group = ttk.Labelframe(parent, text="Mixture of Experts (MoE)", padding="10")
        moe_group.pack(fill=tk.X, pady=5)
        
        self.moe_cpu_layers = tk.StringVar(value="")
        self.create_entry(moe_group, "MoE CPU Layers (--n-cpu-moe):", self.moe_cpu_layers, "Number of MoE layers to run on the CPU (optional).", row=0)

        # --- Custom Arguments ---
        custom_group = ttk.Labelframe(parent, text="Custom Arguments", padding="10")
        custom_group.pack(fill=tk.X, expand=True, pady=5)
        
        self.custom_args = tk.StringVar()
        self.create_entry(custom_group, "Custom Arguments:", self.custom_args, "Enter any other command-line arguments, separated by spaces.", row=0)
    
    def setup_output_tab(self, parent):
        """Sets up the server output log view."""
        ttk.Label(parent, text="Server Log Output:").pack(anchor=tk.W, pady=(0, 5))
        
        # Use a monospace font for better log readability
        monospace_font = font.Font(family="Consolas", size=10)
        
        self.output_text = scrolledtext.ScrolledText(parent, height=25, wrap=tk.WORD, font=monospace_font)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        clear_btn = ttk.Button(parent, text="Clear Output", command=self.clear_output)
        clear_btn.pack(pady=(10, 0), anchor=tk.E)
        ToolTip(clear_btn, "Clear all text from the log output window.")

    # --- UI Helper Methods ---
    def create_entry(self, parent, label_text, string_var, tooltip_text, row):
        """Creates a labeled entry widget with a tooltip."""
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        
        entry = ttk.Entry(parent, textvariable=string_var, width=30)
        entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        parent.columnconfigure(1, weight=1)
        
        ToolTip(label, tooltip_text)
        ToolTip(entry, tooltip_text)
        return entry

    def create_slider(self, parent, label_text, int_var, tooltip_text, from_, to, resolution, row):
        """Creates a labeled slider widget with a tooltip and value display."""
        # Main frame for the slider row
        slider_frame = ttk.Frame(parent)
        slider_frame.grid(row=row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        parent.columnconfigure(0, weight=1)
        
        # Label
        label = ttk.Label(slider_frame, text=label_text)
        label.pack(anchor=tk.W)
        ToolTip(label, tooltip_text)
        
        # Frame for slider and value
        control_frame = ttk.Frame(slider_frame)
        control_frame.pack(fill=tk.X, pady=(2, 0))
        
        # Slider
        slider = ttk.Scale(control_frame, from_=from_, to=to, orient=tk.HORIZONTAL, 
                          variable=int_var, command=lambda v: self.update_slider_label(int_var, value_label, resolution))
        slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ToolTip(slider, tooltip_text)
        
        # Value label
        value_label = ttk.Label(control_frame, text=str(int_var.get()), width=8, anchor=tk.CENTER, relief=tk.SUNKEN)
        value_label.pack(side=tk.RIGHT)
        
        # Set initial value display
        self.update_slider_label(int_var, value_label, resolution)
        
        return slider

    def update_slider_label(self, int_var, label, resolution):
        """Updates the value label next to a slider."""
        # Round to the nearest resolution step
        raw_value = int_var.get()
        rounded_value = round(raw_value / resolution) * resolution
        int_var.set(rounded_value)
        label.config(text=str(rounded_value))

    def create_checkbutton(self, parent, text, variable, tooltip_text):
        """Creates a checkbutton with a tooltip."""
        cb = ttk.Checkbutton(parent, text=text, variable=variable)
        cb.pack(anchor=tk.W, padx=5, pady=2)
        ToolTip(cb, tooltip_text)
        return cb
    
    def create_button(self, parent, text, command, tooltip_text, state=tk.NORMAL, style=None):
        """Creates a button with a tooltip."""
        kwargs = {'style': style} if style else {}
        btn = ttk.Button(parent, text=text, command=command, state=state, **kwargs)
        btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(btn, tooltip_text)
        return btn

    # --- Core Functionality ---
    def browse_model(self):
        filename = filedialog.askopenfilename(
            title="Select Model File",
            filetypes=[("GGUF files", "*.gguf"), ("All files", "*.*")]
        )
        if filename:
            self.model_path.set(filename)
            
    def generate_command(self):
        cmd = ["llama-server"]
        
        if not self.model_path.get().strip():
            messagebox.showerror("Error", "Model path is required!")
            return None
        
        cmd.extend(["-m", self.model_path.get().strip()])
        
        # Add arguments - now using int values for sliders
        cmd.extend(['-c', str(self.ctx_size.get())])
        cmd.extend(['-ngl', str(self.gpu_layers.get())])
        
        # Add other string arguments if their values are not empty
        args = {
            '--port': self.port, '--n-cpu-moe': self.moe_cpu_layers, 
            '-t': self.threads, '-b': self.batch_size, '-np': self.parallel
        }
        for flag, var in args.items():
            if var.get().strip():
                cmd.extend([flag, var.get().strip()])
        
        # Boolean flags
        bool_args = {
            '--jinja': self.jinja, '-fa': self.flash_attn, '--no-mmap': self.no_mmap,
            '--no-webui': self.no_webui, '-cb': self.cont_batching,
            '--mlock': self.mlock
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
        if not cmd:
            return
            
        command_str = " ".join(cmd)
        
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
        if self.is_running:
            return
            
        cmd = self.generate_command()
        if not cmd:
            return
            
        self.output_text.delete(1.0, tk.END)
        self.update_output(f"▶ Starting server with command:\n{' '.join(cmd)}\n\n" + "="*80 + "\n")
        
        def run_server():
            try:
                self.server_process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    universal_newlines=False, bufsize=1
                )
                
                for line_bytes in iter(self.server_process.stdout.readline, b''):
                    try:
                        line = line_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        line = line_bytes.decode('latin-1', errors='replace')
                    
                    self.root.after(0, self.update_output, line)

                self.server_process.wait()
                self.root.after(0, self.server_stopped)
                
            except Exception as e:
                self.root.after(0, self.update_output, f"\n❌ Error starting server: {e}\n")
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
                self.update_output(f"\n❌ Error stopping server: {e}\n")
                
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
            'model_path': self.model_path.get(), 'ctx_size': self.ctx_size.get(),
            'gpu_layers': self.gpu_layers.get(), 'port': self.port.get(),
            'jinja': self.jinja.get(), 'flash_attn': self.flash_attn.get(),
            'no_mmap': self.no_mmap.get(), 'no_webui': self.no_webui.get(),
            'moe_cpu_layers': self.moe_cpu_layers.get(), 'threads': self.threads.get(),
            'batch_size': self.batch_size.get(), 'parallel': self.parallel.get(),
            'cont_batching': self.cont_batching.get(), 'mlock': self.mlock.get(),
            'numa': self.numa.get(), 'custom_args': self.custom_args.get()
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Success", f"Configuration saved to {self.config_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
            
    def load_config(self):
        if not os.path.exists(self.config_file):
            return
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            self.model_path.set(config.get('model_path', ''))
            self.ctx_size.set(config.get('ctx_size', 4096))
            self.gpu_layers.set(config.get('gpu_layers', 99))
            self.port.set(config.get('port', '8080'))
            self.jinja.set(config.get('jinja', True))
            self.flash_attn.set(config.get('flash_attn', False))
            self.no_mmap.set(config.get('no_mmap', False))
            self.no_webui.set(config.get('no_webui', False))
            self.moe_cpu_layers.set(config.get('moe_cpu_layers', ''))
            self.threads.set(config.get('threads', ''))
            self.batch_size.set(config.get('batch_size', ''))
            self.parallel.set(config.get('parallel', ''))
            self.cont_batching.set(config.get('cont_batching', True))
            self.mlock.set(config.get('mlock', False))
            self.numa.set(config.get('numa', False))
            self.custom_args.set(config.get('custom_args', ''))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {e}")

    def open_browser(self):
        """Opens the web browser at the server's port."""
        url = f"http://localhost:{self.port.get().strip()}"
        try:
            webbrowser.open(url)
            self.update_output(f"🌐 Opened browser at {url}\n")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open browser: {e}")


def main():
    root = tk.Tk()
    app = LlamaServerGUI(root)
    
    def on_closing():
        if not app.is_running:
            root.destroy()
            return

        response = messagebox.askyesnocancel(
            "Server Still Running",
            "The LLaMA server is active. Do you want to stop it before exiting?",
            detail="• Yes: Stop the server and exit.\n"
                   "• No: Exit and leave the server running in the background.\n"
                   "• Cancel: Return to the application.",
            icon=messagebox.WARNING
        )
        if response is True:  # Yes
            app.stop_server()
            # Give the server a moment to shut down before destroying the window
            root.after(1000, root.destroy)
        elif response is False:  # No
            root.destroy()
        # On Cancel, do nothing
            
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()