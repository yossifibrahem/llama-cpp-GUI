# LLaMA Server GUI Manager

A comprehensive graphical user interface for managing and configuring the `llama-server` executable from the llama.cpp project. This application provides an intuitive way to configure, start, stop, and monitor your local LLaMA server without dealing with complex command-line arguments.

## Features

### 🎛️ Complete Configuration Management
- **Model Configuration**: Load GGUF models, LoRA adapters, and multimodal projectors
- **Chat Templates**: Support for various chat templates (llama3, chatml, mistral, etc.)
- **Generation Parameters**: Fine-tune sampling settings (temperature, top-k, top-p, etc.)
- **Performance Tuning**: Configure GPU layers, context size, batch sizes, and threading
- **Advanced Features**: Speculative decoding, continuous batching, flash attention

### 🖥️ User-Friendly Interface
- **Tabbed Layout**: Organized sections for different configuration areas
- **Interactive Controls**: Sliders, dropdowns, and input fields with tooltips
- **Real-time Validation**: Input validation and helpful error messages
- **Custom Arguments**: Add any additional llama-server arguments not covered by the GUI

### 💾 Configuration Management
- **Save/Load Configs**: Persistent JSON-based configuration storage
- **Portable Settings**: Config files stored alongside the executable
- **Backup-Friendly**: Human-readable JSON configuration format

### 🔧 Server Management
- **One-Click Start/Stop**: Easy server process management
- **Live Output Monitoring**: Real-time server log display
- **Browser Integration**: Quick access to the web UI
- **System Tray Support**: Minimize to tray and run in background (optional)

<img width="410" alt="Screenshot 2025-09-10 164907" src="https://github.com/user-attachments/assets/a5bb3f07-abb7-4095-a5bd-5928b3741286" />
<img width="410" alt="Screenshot 2025-09-10 164914" src="https://github.com/user-attachments/assets/7c89b4f8-9cfd-44f2-9b0e-a809b50464b8" />
<img width="400" alt="Screenshot 2025-09-10 164917" src="https://github.com/user-attachments/assets/459385c2-b296-40ec-9290-553e31176b65" />
<img width="400" alt="Screenshot 2025-09-10 164921" src="https://github.com/user-attachments/assets/1522191c-5e96-47c4-b7b1-0a0a785779c3" />
<img width="400" alt="Screenshot 2025-09-10 164924" src="https://github.com/user-attachments/assets/51e9d56a-97df-4196-9f76-9d04f4be02bf" />
<img width="400" alt="Screenshot 2025-09-10 170830" src="https://github.com/user-attachments/assets/8726915e-c689-4cf4-bca6-51b7fa7520fc" />
<img width="400" alt="Screenshot 2025-09-10 165115" src="https://github.com/user-attachments/assets/f0d07dad-feac-47e0-9b00-8cc5abc560bd" />
<img width="400" alt="Screenshot 2025-09-10 170815" src="https://github.com/user-attachments/assets/a7fe1576-9f89-439c-ae50-ca9b02414683" />



## Requirements

- Python 3.7 or higher
- `llama-server` executable (from llama.cpp) in your PATH or application directory
- Required Python packages (automatically installed):
  - `ttkbootstrap`
  - `Pillow` (for system tray icon support)
  - `pystray` (optional, for system tray functionality)

## Installation

### Option 1: Download Pre-built Executable
1. Download the latest release from the GitHub releases page
2. Extract to your desired location
3. Ensure `llama-server` executable is in the same directory or your PATH
4. Run `LLaMA-Server-GUI.exe` (Windows) or `LLaMA-Server-GUI` (Linux/Mac)

### Option 2: Run from Source
1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/llama-server-gui.git
   cd llama-server-gui
   ```

2. Install dependencies:
   ```bash
   pip install ttkbootstrap pillow pystray
   ```

3. Run the application:
   ```bash
   python llama-server_gui_new.py
   ```

### Option 3: Build Your Own Executable
1. Install PyInstaller:
   ```bash
   pip install pyinstaller ttkbootstrap pillow pystray
   ```

2. Run the build script:
   ```bash
   python build_exe.py
   ```

3. Find your executable in the `dist` folder

## Usage

### Quick Start
1. **Load a Model**: Use the "Browse" button in the Models tab to select your GGUF model file
2. **Configure Settings**: Adjust parameters across the different tabs as needed
3. **Start Server**: Click the "Start Server" button
4. **Access Web UI**: Click "Open Browser" to access the llama.cpp web interface

### Configuration Tabs

#### 📁 Models
- **Primary Model**: Select your main GGUF model file
- **Model Extensions**: Add LoRA adapters or multimodal projectors
- **Chat Behavior**: Configure chat templates and reasoning settings

#### ⚙️ Generation
- **Output Control**: Set token limits and generation behavior
- **Sampling Parameters**: Fine-tune creativity and randomness

#### 🚀 Performance
- **Core Performance**: Context size, GPU layers, CPU threads
- **Advanced Throughput**: Parallel processing and continuous batching

#### 🔬 Advanced
- **Memory Optimizations**: Flash attention, memory locking, NUMA settings
- **Speculative Decoding**: Use draft models for faster inference

#### 🌐 Server & API
- **Network Configuration**: Host, port, and API key settings
- **Custom Arguments**: Add any additional llama-server flags
- **Access Control**: Configure web UI and API access

#### 📊 Server Output
- **Live Monitoring**: Real-time server log output
- **Log Management**: Clear output and monitor server status

### Configuration Management
- **Save Config**: Preserve your current settings to `llama_server_config.json`
- **Load Config**: Restore previously saved configurations
- **Portable**: Config file is stored in the application directory

### System Tray (Optional)
When pystray is installed, the application can minimize to the system tray:
- **Minimize to Tray**: Close the window to hide in the system tray
- **Tray Menu**: Right-click the tray icon for quick actions
- **Background Operation**: Keep the server running while GUI is hidden

## Configuration File

The application saves settings in JSON format. Example structure:

```json
{
    "model_path": "/path/to/your/model.gguf",
    "ctx_size": 4096,
    "gpu_layers": 33,
    "host": "127.0.0.1",
    "port": "8080",
    "custom_arguments_list": [
        {
            "value": "--custom-flag value",
            "enabled": true
        }
    ]
}
```

## Troubleshooting

### Common Issues

**"llama-server executable not found"**
- Ensure `llama-server` is in your PATH or the same directory as the GUI
- Download llama.cpp binaries from the official releases

**"Module not found" errors**
- Install missing dependencies: `pip install ttkbootstrap pillow pystray`
- For source installation, ensure all requirements are met

**Server won't start**
- Check that your model path is correct and the file exists
- Verify you have sufficient GPU memory for the selected GPU layers
- Review the Server Output tab for detailed error messages

**Performance issues**
- Reduce context size for lower memory usage
- Adjust GPU layers based on your hardware capabilities
- Use smaller batch sizes for memory-constrained systems

### Getting Help
- Check the Server Output tab for detailed error messages
- Review the generated command using "Generate Command" button
- Consult the llama.cpp documentation for parameter details

## Building from Source

### Development Setup
```bash
git clone https://github.com/yourusername/llama-server-gui.git
cd llama-server-gui
pip install -r requirements.txt
python llama-server_gui_new.py
```

### Building Executable
The included `build_exe.py` script uses PyInstaller to create a standalone executable:

```bash
python build_exe.py
```

This creates a single executable file in the `dist` directory that includes all dependencies.

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

### Development Guidelines
- Follow Python PEP 8 style guidelines
- Add tooltips for new UI elements
- Update configuration saving/loading for new parameters
- Test on multiple platforms when possible

## License

This project is released under the MIT License. See the LICENSE file for details.

## Acknowledgments

- Built for the [llama.cpp](https://github.com/ggerganov/llama.cpp) project
- Uses [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) for modern UI theming
- System tray support provided by [pystray](https://github.com/moses-palmer/pystray)

## Changelog

### v1.0.0
- Initial release
- Complete GUI for llama-server configuration
- Configuration save/load functionality
- Real-time server output monitoring
- System tray support
- Cross-platform executable building

---

**Note**: This GUI is a third-party tool for llama.cpp and is not officially affiliated with the llama.cpp project.
