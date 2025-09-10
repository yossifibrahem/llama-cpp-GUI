import sys
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.scrolled import ScrolledText, ScrolledFrame
from ttkbootstrap.tooltip import ToolTip
from tkinter import filedialog

import subprocess
import threading
import os
import json
import webbrowser

try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

class LlamaServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LLaMA Server GUI Manager")
        self.root.geometry("1080x720")
        self.root.minsize(1080, 720)

        # Server process management
        self.server_process = None
        self.is_running = False

        # System tray setup
        self.tray_icon = None
        self.is_in_tray = False

        # Use user's directory for portable config file
        self.config_file = self.get_config_path("llama_server_config.json")

        # Store slider references for updating on load
        self.slider_refs = {}
        
        # Data store for custom arguments
        self.custom_arguments = []

        self.setup_ui()
        self.load_config()

    def get_config_path(self, filename):
        """Get the path for config file that works with PyInstaller."""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            app_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            app_dir = os.path.dirname(os.path.abspath(__file__))
        
        return os.path.join(app_dir, filename)

    def setup_ui(self):
        """Sets up the main UI layout, including notebook and control buttons."""
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)

        # --- Control Buttons (Packed FIRST and anchored to the BOTTOM) ---
        control_frame = ttk.Frame(main_container)
        control_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        # Left-aligned buttons
        left_button_frame = ttk.Frame(control_frame)
        left_button_frame.pack(side=tk.LEFT)
        self.create_button(left_button_frame, "Save Config 💾", self.save_config, "Save the current settings.", bootstyle="secondary")
        self.create_button(left_button_frame, "Load Config 📂", self.load_config, "Load settings from the config file.", bootstyle="secondary")
        self.create_button(left_button_frame, "Generate Command ⚡", self.show_command, "Show the final command to be executed.", bootstyle="info")

        # Right-aligned buttons
        right_button_frame = ttk.Frame(control_frame)
        right_button_frame.pack(side=tk.RIGHT)
        self.browser_button = self.create_button(right_button_frame, "Open Browser 🌐", self.open_browser, "Access the server web UI.", state=tk.DISABLED, bootstyle="primary-outline")
        self.stop_button = self.create_button(right_button_frame, "Stop Server ⏹️", self.stop_server, "Stop the running server process.", state=tk.DISABLED, bootstyle="danger")
        self.start_button = self.create_button(right_button_frame, "Start Server ▶️", self.start_server, "Start the server with current settings.", bootstyle="success")

        # --- Notebook (Packed SECOND to fill the remaining space) ---
        notebook = ttk.Notebook(main_container, bootstyle="primary")
        notebook.pack(fill=tk.BOTH, expand=True)

        # --- Create Tab Frames ---
        model_frame = ttk.Frame(notebook, padding="10")
        generation_frame = ttk.Frame(notebook, padding="10")
        performance_core_frame = ttk.Frame(notebook, padding="10")
        performance_advanced_frame = ttk.Frame(notebook, padding="10")
        server_api_frame = ttk.Frame(notebook, padding="10")
        output_frame = ttk.Frame(notebook, padding="10")

        notebook.add(model_frame, text="  Models ")
        notebook.add(generation_frame, text=" Generation ")
        notebook.add(performance_core_frame, text=" Performance ")
        notebook.add(performance_advanced_frame, text=" Advanced ")
        notebook.add(server_api_frame, text=" Server & API ")
        notebook.add(output_frame, text=" Server Output ")

        # --- Populate Tabs ---
        self.setup_model_tab(model_frame)
        self.setup_generation_tab(generation_frame)
        self.setup_performance_core_tab(performance_core_frame)
        self.setup_performance_advanced_tab(performance_advanced_frame)
        self.setup_server_api_tab(server_api_frame)
        self.setup_output_tab(output_frame)


    # --- Tab Setup Methods ---
    def setup_model_tab(self, parent):
        """Configures the 'Model' tab for model files, extensions, and chat behavior."""
        # --- Primary Model ---
        model_group = ttk.Labelframe(parent, text="Primary Model", padding="10")
        model_group.pack(fill=tk.X, pady=5)
        self.model_path = tk.StringVar()
        self.create_file_entry(model_group, "Model Path (-m):", self.model_path, "Path to the GGUF model file.", ".gguf", row=0)
        self.alias = tk.StringVar()
        self.create_entry(model_group, "Model Alias (-a):", self.alias, "Set an alias for the model (used in API calls).", row=1)

        # --- Model Extensions ---
        ext_group = ttk.Labelframe(parent, text="Model Extensions", padding="10")
        ext_group.pack(fill=tk.X, pady=5)
        self.lora_path = tk.StringVar()
        self.create_file_entry(ext_group, "LoRA Path (--lora):", self.lora_path, "Path to a LoRA adapter file (optional).", ".gguf", row=0)
        self.mmproj_path = tk.StringVar()
        self.create_file_entry(ext_group, "Multimodal Projector (--mmproj):", self.mmproj_path, "Path to a multimodal projector file (for vision models).", ".gguf", row=1)

        # --- Chat Behavior ---
        chat_group = ttk.Labelframe(parent, text="Chat Behavior", padding="10")
        chat_group.pack(fill=tk.X, pady=5)
        self.chat_template = tk.StringVar()
        chat_templates = ["", "bailing", "chatglm3", "chatglm4", "chatml", "command-r", "deepseek", "deepseek2", "gemma", "llama2", "llama3", "mistral", "openchat", "phi3", "vicuna", "zephyr"]
        self.create_combobox(chat_group, "Template (--chat-template):", self.chat_template, "Select a chat template (leave blank for auto-detection).", chat_templates, row=0)

        self.reasoning_format = tk.StringVar()
        reasoning_formats = ["", "auto", "none", "deepseek"]
        self.create_combobox(chat_group, "Reasoning Format (--reasoning-format):", self.reasoning_format, "Controls whether thought tags are allowed and/or extracted from the response.", reasoning_formats, row=1)

        self.reasoning_effort = tk.StringVar()
        reasoning_levels = ["", "low", "medium", "high"]
        self.create_combobox(chat_group, "Reasoning Effort:", self.reasoning_effort, "Set reasoning effort for chat template kwargs (some models).", reasoning_levels, row=2)
        
        self.jinja = tk.BooleanVar(value=False)
        self.create_checkbutton(chat_group, "Enable Jinja (--jinja)", self.jinja, "Enable Jinja2 templating (required for some custom templates).", row=3)

    def setup_generation_tab(self, parent):
        """Configures the 'Generation' tab for sampling and output control."""
        # --- Output Control ---
        output_group = ttk.Labelframe(parent, text="Output Control", padding="10")
        output_group.pack(fill=tk.X, pady=5, side=tk.TOP)
        
        self.n_predict = tk.StringVar(value="")
        self.create_spinbox(output_group, "Tokens to Generate (-n, --n-predict):", self.n_predict, "Number of tokens to generate (default -1 = infinite).", from_=-1, to=131072, increment=1, row=0)
        
        self.ignore_eos = tk.BooleanVar(value=False)
        self.create_checkbutton(output_group, "Ignore End-of-Sequence (--ignore-eos)", self.ignore_eos, "Prevents model from stopping early.", row=1)
        
        # --- Sampling Parameters ---
        sampling_group = ttk.Labelframe(parent, text="Sampling Parameters", padding="10")
        sampling_group.pack(fill=tk.X, pady=5)
        
        self.temp = tk.StringVar(value="")
        self.create_spinbox(sampling_group, "Temperature (--temp):", self.temp, "Creativity level (default 0.8). Lower = deterministic, higher = creative.", from_=0, to=2, increment=0.1, row=0)

        self.top_k = tk.StringVar(value="")
        self.create_spinbox(sampling_group, "Top-K (--top-k):", self.top_k, "Keep only top-k tokens when sampling (default 40).", from_=0, to=1000, increment=1, row=1)
        
        self.top_p = tk.StringVar(value="")
        self.create_spinbox(sampling_group, "Top-P (--top-p):", self.top_p, "Nucleus sampling (default 0.9).", from_=0, to=1, increment=0.1, row=2)

        self.repeat_penalty = tk.StringVar(value="")
        self.create_spinbox(sampling_group, "Repeat Penalty (--repeat-penalty):", self.repeat_penalty, "Penalizes repetition (default 1.0). Increase to reduce loops.", from_=0, to=2, increment=0.1, row=3)

    def setup_performance_core_tab(self, parent):
        """Configures the 'Performance' tab for core speed and throughput settings."""
        # --- Core Performance ---
        core_group = ttk.Labelframe(parent, text="Core Performance", padding="10")
        core_group.pack(fill=tk.X, pady=5, side=tk.TOP)
        self.ctx_size = tk.IntVar(value=4096)
        self.create_slider(core_group, "Context Size (-c):", self.ctx_size, "Context size (sequence length) for the model.", from_=0, to=131072, resolution=1024, row=0)
        self.gpu_layers = tk.IntVar(value=99)
        self.create_slider(core_group, "GPU Layers (-ngl):", self.gpu_layers, "Number of model layers to offload to GPU (99 for all).", from_=0, to=99, resolution=1, row=1)
        self.threads = tk.StringVar(value="")
        self.create_spinbox(core_group, "CPU Threads (-t):", self.threads, "Number of CPU threads to use (e.g., 8).", from_=1, to=128, increment=1, row=2)
        self.batch_size = tk.StringVar(value="")
        self.create_spinbox(core_group, "Batch Size (-b):", self.batch_size, "Batch size for prompt processing (e.g., 2048).", from_=1, to=8192, increment=1, row=3)
        self.ubatch_size = tk.StringVar(value="")
        self.create_spinbox(core_group, "Physical Batch Size (-ub):", self.ubatch_size, "Physical batch size. Lower values reduce VRAM use but slow things down.", from_=1, to=1024, increment=1, row=4)

        # --- Advanced Throughput ---
        throughput_group = ttk.Labelframe(parent, text="Advanced Throughput", padding="10")
        throughput_group.pack(fill=tk.X, pady=5)
        self.parallel = tk.StringVar(value="")
        self.create_spinbox(throughput_group, "Parallel Sequences (-np):", self.parallel, "Number of parallel sequences to process (e.g., 4).", row=0, from_=1, to=16, increment=1)
        self.cont_batching = tk.BooleanVar(value=False)
        self.create_checkbutton(throughput_group, "Continuous Batching (-cb)", self.cont_batching, "Enable continuous batching for higher throughput.", row=1)

    def setup_performance_advanced_tab(self, parent):
        """Configures the 'Advanced' tab for memory, optimizations, and speculative decoding."""
        # --- Memory & Optimizations ---
        mem_group = ttk.Labelframe(parent, text="Memory & Optimizations", padding="10")
        mem_group.pack(fill=tk.X, pady=5)
        self.flash_attn = tk.StringVar(value="auto")
        flash_attn_options = ["on", "off", "auto"]
        self.create_combobox(mem_group, "Flash Attention (-fa):", self.flash_attn, "Set Flash Attention use ('on', 'off', or 'auto', default: 'auto').", flash_attn_options, row=0)
        self.moe_cpu_layers = tk.StringVar(value="")
        self.create_spinbox(mem_group, "MoE CPU Layers (--n-cpu-moe):", self.moe_cpu_layers, "MoE layers to keep on CPU if model doesn't fit on GPU.", row=1, from_=0, to=99, increment=1)
        self.mlock = tk.BooleanVar(value=False)
        self.create_checkbutton(mem_group, "Memory Lock (--mlock)", self.mlock, "Lock model in RAM to prevent swapping.", row=2)
        self.no_mmap = tk.BooleanVar(value=False)
        self.create_checkbutton(mem_group, "No Memory Mapping (--no-mmap)", self.no_mmap, "Disable memory mapping of the model file.", row=3)
        self.numa = tk.BooleanVar(value=False)
        self.create_checkbutton(mem_group, "NUMA Optimizations (--numa)", self.numa, "Enable NUMA-aware optimizations for specific hardware.", row=4)

        # --- Speculative Decoding ---
        spec_group = ttk.Labelframe(parent, text="Speculative Decoding", padding="10")
        spec_group.pack(fill=tk.X, pady=5)
        self.draft_model_path = tk.StringVar()
        self.create_file_entry(spec_group, "Draft Model (-md):", self.draft_model_path, "Path to the draft model for speculative decoding.", ".gguf", row=0)
        self.draft_gpu_layers = tk.StringVar(value="")
        self.create_spinbox(spec_group, "Draft GPU Layers (-ngld):", self.draft_gpu_layers, "Number of GPU layers for the draft model.", row=1, from_=0, to=99, increment=1)
        self.draft_tokens = tk.StringVar(value="")
        self.create_spinbox(spec_group, "Draft Tokens (--draft):", self.draft_tokens, "Number of tokens to draft (e.g., 5).", row=2, from_=1, to=1024, increment=1)

    def setup_server_api_tab(self, parent):
        """Configures the 'Server & API' tab for network, access, and logging."""
        parent.rowconfigure(2, weight=1) # Allow custom args group to expand
        parent.columnconfigure(0, weight=1)
        
        # --- Network Configuration ---
        net_group = ttk.Labelframe(parent, text="Network Configuration", padding="10")
        net_group.grid(row=0, column=0, sticky=EW, pady=5)
        net_group.columnconfigure(1, weight=1)
        self.host = tk.StringVar(value="127.0.0.1")
        self.create_entry(net_group, "Host (--host):", self.host, "IP address to listen on (0.0.0.0 for network access).", row=0)
        self.port = tk.StringVar(value="8080")
        self.create_entry(net_group, "Port (--port):", self.port, "Network port for the server to listen on.", row=1)

        # --- Access & Features ---
        access_group = ttk.Labelframe(parent, text="Access & Features", padding="10")
        access_group.grid(row=1, column=0, sticky=EW, pady=5)
        access_group.columnconfigure(1, weight=1)
        self.api_key = tk.StringVar()
        self.create_entry(access_group, "API Key (--api-key):", self.api_key, "API key for bearer token authentication (optional).", row=0)
        self.no_webui = tk.BooleanVar(value=False)
        self.create_checkbutton(access_group, "Disable Web UI (--no-webui)", self.no_webui, "Disable the built-in web interface.", row=1)
        self.embedding = tk.BooleanVar(value=False)
        self.create_checkbutton(access_group, "Embeddings Only (--embedding)", self.embedding, "Enable embedding-only mode (disables chat).", row=2)

        # --- Custom Arguments Management ---
        custom_group = ttk.Labelframe(parent, text="Custom Arguments Management", padding="10")
        custom_group.grid(row=2, column=0, sticky=NSEW, pady=5)
        custom_group.columnconfigure(0, weight=1)
        custom_group.rowconfigure(1, weight=1)

        # Input for new argument
        add_arg_frame = ttk.Frame(custom_group)
        add_arg_frame.grid(row=0, column=0, sticky=EW, pady=(0, 10))
        add_arg_frame.columnconfigure(0, weight=1)
        self.new_arg_entry = ttk.Entry(add_arg_frame)
        self.new_arg_entry.grid(row=0, column=0, sticky=EW, padx=(0, 5))
        ToolTip(self.new_arg_entry, "Enter a full argument with its value (e.g., --my-flag value) and press Add.")
        add_button = ttk.Button(add_arg_frame, text="Add", command=self.add_custom_argument, bootstyle="success-outline")
        add_button.grid(row=0, column=1, sticky=E)

        # Scrollable list for existing arguments
        self.custom_args_list_frame = ScrolledFrame(custom_group, autohide=True, bootstyle="round")
        self.custom_args_list_frame.grid(row=1, column=0, sticky=NSEW)
        
        # Other options below the list
        other_options_frame = ttk.Frame(custom_group)
        other_options_frame.grid(row=2, column=0, sticky=EW, pady=(10, 0))
        self.verbose = tk.BooleanVar(value=False)
        verbose_cb = ttk.Checkbutton(other_options_frame, text="Verbose Logging (-v)", variable=self.verbose, bootstyle="round-toggle")
        verbose_cb.pack(side=tk.LEFT)
        ToolTip(verbose_cb, "Enable verbose server logging for debugging.")
        
    def setup_output_tab(self, parent):
        """Sets up the server output log view."""
        ttk.Label(parent, text="Server Log Output:").pack(anchor=tk.W, pady=(0, 5))
        monospace_font = ("Consolas", 10)
        self.output_text = ScrolledText(parent, height=20, wrap=tk.WORD, font=monospace_font, autohide=True)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        clear_btn = ttk.Button(parent, text="Clear Output", command=self.clear_output, bootstyle="secondary-outline")
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
        browse_btn = ttk.Button(file_path_frame, text="Browse", command=lambda: self.browse_file(string_var, file_ext), bootstyle="primary")
        browse_btn.pack(side=tk.RIGHT)
        ToolTip(label, text=tooltip_text)
        ToolTip(entry, text=tooltip_text)
        ToolTip(browse_btn, text=f"Select a {file_ext} file.")

    def create_entry(self, parent, label_text, string_var, tooltip_text, row):
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        entry = ttk.Entry(parent, textvariable=string_var, width=30)
        entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        parent.columnconfigure(1, weight=1)
        ToolTip(label, text=tooltip_text)
        ToolTip(entry, text=tooltip_text)
    
    def create_spinbox(self, parent, label_text, variable, tooltip_text, from_, to, increment, row):
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)

        spin = ttk.Spinbox(
            parent, 
            textvariable=variable,
            from_=from_, 
            to=to, 
            increment=increment,
            width=10,
            bootstyle="primary"
        )
        spin.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        ToolTip(label, text=tooltip_text)
        ToolTip(spin, text=tooltip_text)
        return spin

    def create_combobox(self, parent, label_text, string_var, tooltip_text, values, row):
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        combobox = ttk.Combobox(parent, textvariable=string_var, values=values)
        combobox.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        parent.columnconfigure(1, weight=1)
        ToolTip(label, text=tooltip_text)
        ToolTip(combobox, text=tooltip_text)
        
    def create_slider(self, parent, label_text, int_var, tooltip_text, from_, to, resolution, row):
        slider_frame = ttk.Frame(parent)
        slider_frame.grid(row=row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        parent.columnconfigure(1, weight=1)
        label = ttk.Label(slider_frame, text=label_text)
        label.pack(anchor=tk.W)
        ToolTip(label, text=tooltip_text)
        control_frame = ttk.Frame(slider_frame)
        control_frame.pack(fill=tk.X, pady=(2, 0))
        slider = ttk.Scale(control_frame, from_=from_, to=to, orient=tk.HORIZONTAL,
                           variable=int_var, command=lambda v: self.update_slider_label(int_var, value_label, resolution), bootstyle="primary")
        slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ToolTip(slider, text=tooltip_text)
        value_label = ttk.Label(control_frame, text=str(int_var.get()), width=8, anchor=tk.CENTER)
        value_label.pack(side=tk.RIGHT)
        
        slider_key = f"{label_text}_{id(int_var)}"
        self.slider_refs[slider_key] = {'var': int_var, 'slider': slider, 'label': value_label, 'resolution': resolution}
        self.update_slider_label(int_var, value_label, resolution)

    def update_slider_label(self, int_var, label, resolution):
        raw_value = int_var.get()
        rounded_value = round(raw_value / resolution) * resolution
        int_var.set(rounded_value)
        label.config(text=str(rounded_value))

    def update_all_sliders(self):
        for key, refs in self.slider_refs.items():
            refs['slider'].set(refs['var'].get())
            self.update_slider_label(refs['var'], refs['label'], refs['resolution'])

    def create_checkbutton(self, parent, text, variable, tooltip_text, row):
        cb = ttk.Checkbutton(parent, text=text, variable=variable, bootstyle="round-toggle")
        cb.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        ToolTip(cb, text=tooltip_text)

    def create_button(self, parent, text, command, tooltip_text, state=tk.NORMAL, bootstyle="primary"):
        btn = ttk.Button(parent, text=text, command=command, state=state, bootstyle=bootstyle)
        btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(btn, text=tooltip_text)
        return btn

    # --- Custom Argument Methods ---
    def add_custom_argument(self):
        arg_text = self.new_arg_entry.get().strip()
        if not arg_text:
            return
        if any(arg['value'] == arg_text for arg in self.custom_arguments):
            Messagebox.show_warning("This argument already exists in the list.", "Duplicate Argument")
            return
            
        self.custom_arguments.append({"value": arg_text, "enabled": True})
        self.new_arg_entry.delete(0, tk.END)
        self.rebuild_custom_args_list()

    def delete_custom_argument(self, arg_to_delete):
        self.custom_arguments.remove(arg_to_delete)
        self.rebuild_custom_args_list()
        
    def rebuild_custom_args_list(self):
        for widget in self.custom_args_list_frame.winfo_children():
            widget.destroy()

        for arg_item in self.custom_arguments:
            row_frame = ttk.Frame(self.custom_args_list_frame, padding=(5, 3))
            row_frame.pack(fill=X, expand=True, padx=(0, 5)) 

            is_enabled_var = tk.BooleanVar(value=arg_item.get("enabled", True))
            
            def on_toggle(item=arg_item, var=is_enabled_var):
                item["enabled"] = var.get()

            toggle = ttk.Checkbutton(row_frame, variable=is_enabled_var, bootstyle="round-toggle", command=on_toggle)
            toggle.pack(side=LEFT, padx=(0, 10))

            label = ttk.Label(row_frame, text=arg_item["value"])
            delete_btn = ttk.Button(row_frame, text="Delete", bootstyle="danger-link", command=lambda item=arg_item: self.delete_custom_argument(item))
            
            # Pack order matters: label is packed after edit logic is set up.
            delete_btn.pack(side=RIGHT, padx=(10, 0))
            
            ### ADDED ### Logic for double-click-to-edit
            def start_edit(event, item, lbl, frame, del_btn):
                lbl.pack_forget() # Hide the label

                entry_var = tk.StringVar(value=item["value"])
                edit_entry = ttk.Entry(frame, textvariable=entry_var)
                edit_entry.pack(side=LEFT, fill=X, expand=True, before=del_btn)
                edit_entry.focus_set()
                edit_entry.selection_range(0, tk.END)

                def save_edit(event):
                    new_value = entry_var.get().strip()
                    if new_value:
                        item["value"] = new_value
                        lbl.config(text=new_value)
                    
                    edit_entry.destroy()
                    lbl.pack(side=LEFT, fill=X, expand=True, before=del_btn) # Show the label again

                edit_entry.bind("<Return>", save_edit)
                edit_entry.bind("<FocusOut>", save_edit)

            label.bind("<Double-1>", lambda e, item=arg_item, lbl=label, frame=row_frame, btn=delete_btn: start_edit(e, item, lbl, frame, btn))
            ToolTip(label, "Double-click to edit this argument.")
            label.pack(side=LEFT, fill=X, expand=True, anchor=W)


    # --- Core Functionality ---
    def browse_file(self, string_var, file_ext):
        filename = filedialog.askopenfilename(
            title=f"Select {file_ext} File",
            filetypes=[(f"{file_ext.upper()} files", f"*{file_ext}"), ("All files", "*.*")]
        )
        if filename:
            string_var.set(filename)

    def generate_command(self):
        if not self.model_path.get().strip():
            Messagebox.show_error("Model path is required!", "Error")
            return None
        
        cmd = ["llama-server", "-m", self.model_path.get().strip()]
        cmd.extend(['-c', str(self.ctx_size.get())])
        cmd.extend(['-ngl', str(self.gpu_layers.get())])
        
        args = {
            '--host': self.host, '--port': self.port, '-a': self.alias,
            '--api-key': self.api_key, '-t': self.threads, '-b': self.batch_size, 
            '-np': self.parallel, '--lora': self.lora_path,
            '--mmproj': self.mmproj_path, '--chat-template': self.chat_template,
            '-md': self.draft_model_path, '-ngld': self.draft_gpu_layers,
            '--draft': self.draft_tokens, '--n-cpu-moe': self.moe_cpu_layers,
            '--reasoning-format': self.reasoning_format, '-ub': self.ubatch_size,
            '-n': self.n_predict, '--temp': self.temp, '--top-k': self.top_k,
            '--top-p': self.top_p, '--repeat-penalty': self.repeat_penalty
        }
        for flag, var in args.items():
            if var.get().strip():
                cmd.extend([flag, var.get().strip()])
        
        if self.reasoning_effort.get().strip():
            kwargs_json = json.dumps({"reasoning_effort": self.reasoning_effort.get()})
            cmd.extend(['--chat-template-kwargs', kwargs_json])
        
        # Handle flash attention as a special case since it needs a value
        if self.flash_attn.get().strip() and self.flash_attn.get().strip() != "auto":
            cmd.extend(['-fa', self.flash_attn.get().strip()])
        
        bool_args = {
            '--no-mmap': self.no_mmap,
            '--no-webui': self.no_webui, '-cb': self.cont_batching,
            '--mlock': self.mlock, '--embedding': self.embedding,
            '--jinja': self.jinja, '-v': self.verbose,
            '--ignore-eos': self.ignore_eos
        }
        for flag, var in bool_args.items():
            if var.get():
                cmd.append(flag)

        if self.numa.get():
            cmd.extend(["--numa", "distribute"])
            
        # Add enabled custom arguments from the list
        for arg_item in self.custom_arguments:
            if arg_item.get("enabled", False) and arg_item.get("value", "").strip():
                cmd.extend(arg_item["value"].strip().split())
            
        return cmd

    def show_command(self):
        cmd = self.generate_command()
        if not cmd: return
        command_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in cmd)
        cmd_window = ttk.Toplevel(self.root)
        cmd_window.title("Generated Command")
        cmd_window.geometry("1200x300")
        ttk.Label(cmd_window, text="Generated Command:", padding="10 10 0 5").pack(anchor=tk.W)
        cmd_text = ScrolledText(cmd_window, height=5, wrap=tk.WORD, autohide=True)
        cmd_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        cmd_text.insert(tk.END, command_str)
        cmd_text.text.configure(state=tk.DISABLED)
        
        def copy_command():
            cmd_window.clipboard_clear()
            cmd_window.clipboard_append(command_str)
            Messagebox.ok("Command copied to clipboard!", "Copied", parent=cmd_window)
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
                self.root.after(0, self.update_output, f"\n⚠ Error: 'llama-server' executable not found. Ensure it's in the PATH or same directory.\n")
                self.root.after(0, self.server_stopped)
            except Exception as e:
                self.root.after(0, self.update_output, f"\n⚠ Error starting server: {e}\n")
                self.root.after(0, self.server_stopped)
        
        threading.Thread(target=run_server, daemon=True).start()
        
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
            'model_path': self.model_path.get(), 'alias': self.alias.get(),
            'lora_path': self.lora_path.get(), 'mmproj_path': self.mmproj_path.get(),
            'chat_template': self.chat_template.get(), 'reasoning_effort': self.reasoning_effort.get(),
            'jinja': self.jinja.get(), 'ctx_size': self.ctx_size.get(),
            'gpu_layers': self.gpu_layers.get(), 'threads': self.threads.get(),
            'batch_size': self.batch_size.get(), 'cont_batching': self.cont_batching.get(),
            'parallel': self.parallel.get(), 'flash_attn': self.flash_attn.get(),
            'mlock': self.mlock.get(), 'no_mmap': self.no_mmap.get(), 'numa': self.numa.get(),
            'moe_cpu_layers': self.moe_cpu_layers.get(), 'draft_model_path': self.draft_model_path.get(),
            'draft_gpu_layers': self.draft_gpu_layers.get(), 'draft_tokens': self.draft_tokens.get(),
            'host': self.host.get(), 'port': self.port.get(), 'api_key': self.api_key.get(),
            'no_webui': self.no_webui.get(), 'embedding': self.embedding.get(),
            'verbose': self.verbose.get(), 'custom_arguments_list': self.custom_arguments,
            'reasoning_format': self.reasoning_format.get(), 'ubatch_size': self.ubatch_size.get(),
            'n_predict': self.n_predict.get(), 'ignore_eos': self.ignore_eos.get(),
            'temp': self.temp.get(), 'top_k': self.top_k.get(), 'top_p': self.top_p.get(),
            'repeat_penalty': self.repeat_penalty.get()
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            Messagebox.ok(f"Configuration saved to {self.config_file}", "Success")
        except Exception as e:
            Messagebox.show_error(f"Failed to save configuration: {e}", "Error")

    def load_config(self):
        if not os.path.exists(self.config_file): return
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Load values, providing defaults for missing keys
            self.model_path.set(config.get('model_path', ''))
            self.alias.set(config.get('alias', ''))
            self.lora_path.set(config.get('lora_path', ''))
            self.mmproj_path.set(config.get('mmproj_path', ''))
            self.chat_template.set(config.get('chat_template', ''))
            self.reasoning_effort.set(config.get('reasoning_effort', ''))
            self.jinja.set(config.get('jinja', False))
            self.ctx_size.set(config.get('ctx_size', 4096))
            self.gpu_layers.set(config.get('gpu_layers', 99))
            self.threads.set(config.get('threads', ''))
            self.batch_size.set(config.get('batch_size', ''))
            self.cont_batching.set(config.get('cont_batching', False))
            self.parallel.set(config.get('parallel', ''))
            self.flash_attn.set(config.get('flash_attn', False))
            self.mlock.set(config.get('mlock', False))
            self.no_mmap.set(config.get('no_mmap', False))
            self.numa.set(config.get('numa', False))
            self.moe_cpu_layers.set(config.get('moe_cpu_layers', ''))
            self.draft_model_path.set(config.get('draft_model_path', ''))
            self.draft_gpu_layers.set(config.get('draft_gpu_layers', ''))
            self.draft_tokens.set(config.get('draft_tokens', ''))
            self.host.set(config.get('host', '127.0.0.1'))
            self.port.set(config.get('port', '8080'))
            self.api_key.set(config.get('api_key', ''))
            self.no_webui.set(config.get('no_webui', False))
            self.embedding.set(config.get('embedding', False))
            self.verbose.set(config.get('verbose', False))

            # Load new custom arguments list
            self.custom_arguments = config.get('custom_arguments_list', [])
            # Backward compatibility for old 'custom_args' string
            if not self.custom_arguments and 'custom_args' in config:
                old_args_str = config['custom_args'].strip()
                if old_args_str:
                    self.custom_arguments.append({"value": old_args_str, "enabled": True})
            self.rebuild_custom_args_list()

            self.reasoning_format.set(config.get('reasoning_format', ''))
            self.ubatch_size.set(config.get('ubatch_size', ''))
            self.n_predict.set(config.get('n_predict', ''))
            self.ignore_eos.set(config.get('ignore_eos', False))
            self.temp.set(config.get('temp', ''))
            self.top_k.set(config.get('top_k', ''))
            self.top_p.set(config.get('top_p', ''))
            self.repeat_penalty.set(config.get('repeat_penalty', ''))
            
            self.update_all_sliders()
        except Exception as e:
            Messagebox.show_error(f"Failed to load configuration: {e}", "Error")

    def open_browser(self):
        host = self.host.get().strip()
        if host == '0.0.0.0': host = 'localhost'
        url = f"http://{host}:{self.port.get().strip()}"
        try:
            webbrowser.open(url)
            self.update_output(f"🌐 Opened browser at {url}\n")
        except Exception as e:
            Messagebox.show_error(f"Failed to open browser: {e}", "Error")

        # --- Tray Management ---
    def create_tray_icon(self):
        """Create system tray icon with menu."""
        if not TRAY_AVAILABLE:
            return None

        image = self.load_app_icon()
        menu_items = [
            item('Show Window', self.show_window),
            item('Open Browser', self.open_browser_from_tray, enabled=lambda i: self.is_running),
            pystray.Menu.SEPARATOR,
            item('Quit Application', self.quit_application),
        ]
        icon = pystray.Icon("llama_server", image, "LLaMA Server", menu=pystray.Menu(*menu_items))
        return icon

    def load_app_icon(self):
        """Load app icon for tray (fallback to blank)."""
        try:
            return Image.open(resource_path("llama-cpp.ico"))
        except Exception:
            return Image.new("RGB", (64, 64), color=(0, 0, 0))

    def show_window(self, icon=None, item=None):
        """Restore window from tray."""
        self.root.after(0, self.root.deiconify)

    def open_browser_from_tray(self, icon=None, item=None):
        """Open browser when clicked from tray."""
        self.root.after(0, self.open_browser)

    def quit_application(self, icon=None, item=None):
        """Quit app from tray."""
        if self.server_process:
            self.server_process.terminate()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)

    def hide_to_tray(self):
        """Hide window and show tray icon."""
        self.root.withdraw()
        if self.tray_icon is None:
            self.tray_icon = self.create_tray_icon()
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

            
def resource_path(filename):
    """Get absolute path to resource, works for dev and for PyInstaller bundle"""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)

def main():
    root = ttk.Window(themename="cosmo")
    
    try:
        icon_path = resource_path("llama-cpp.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass
    
    app = LlamaServerGUI(root)

    def on_closing():
        if app.is_running and TRAY_AVAILABLE:
            app.hide_to_tray()
        else:
            if app.server_process:
                app.server_process.terminate()
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()



if __name__ == "__main__":
    main()