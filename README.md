# STM-Graph Graphic User Interface (v1.0.0)
[![ACM CIKM ’25 — Resource Paper](https://img.shields.io/badge/ACM%20CIKM%20%E2%80%9925-Resource%20Paper-blueviolet)](https://doi.org/10.1145/3746252.3761645)
[![DOI](https://img.shields.io/badge/DOI-10.1145%2F3746252.3761645-2ea44f)](https://doi.org/10.1145/3746252.3761645)
> 🏆 **Accepted at ACM CIKM ’25 (Resource Track)** — November 10–14, 2025, Seoul. [Read the paper](https://doi.org/10.1145/3746252.3761645)

This is the official _"code-free"_ version of [STM-Graph](https://github.com/Ahghaffari/stm_graph) python library, suitable for users who prefer a graphical interface to interact with the library's features. The GUI is designed to simplify the process of working with urban datasets, from data generation to model training, without requiring extensive programming knowledge.


On this page, you can find the installation instructions, a brief overview of the features, and how to use the GUI.


## Features
- **Interactive Visualization**: Easily visualize urban datasets with interactive graphs and maps. Users can zoom, navigate images and save in PNG, SVG and PDF formats.

- **Complete Data Generation Pipeline**: A sequence of steps to generate graph data from raw datasets. Users can load raw data, preprocess it, map it to spatial features, and generate graph data for training phase. Each step is modular and can be customized based on user requirements.

- **Model Training**: Train various state-of-the-art networks on generated temporal graph datasets. The GUI provides options to select different models, configure both training's and model's hyperparameters.

- **Logging**: The GUI provides options for users to track their training with [Weights & Biases (W&B)](https://wandb.ai/) or via local log print. 

## GUI Structure
Once you have launched the GUI, you will see a user-friendly interface with two main tabs: **_Data_** and **_Training_**, structured as follows:

```
├── STM-Graph GUI
│   ├── Data
│   │   ├── Input                 # Load raw data, preview data, choose time and graphical information
│   │   ├── Config                # Configure general parameters for data processing and graph generation
│   │   ├── Data_VIS              # Visualize the processed data (interactively)
│   │   ├── Mapping               # Configure mapping methods and parameters
│   │   ├── Mapping_VIS           # Visualize mapping results before generating graph data (interactively)
│   │   └── Graph_Data_VIS        # Visualize the generated graph data with various plot types (interactively)
│   └── Training
│       ├── Model                 # Load graphed data, configure training and model parameters
│       └── Training_and_Logging  # Set up log tracking and start training (near real-time logging on local)
```

## Installation

### Create a new environment for example, using `conda`:
```bash
conda create -n stmgraph-gui python=3.8.20
```
### Activate the environment
```bash
conda activate stmgraph-gui
```
### Install the base package
```bash
pip install stm-gnn
```
### Install PyTorch
*Choose one of the following commands based on your system configuration.*

   - CUDA with GPU support
      ```bash
      pip install torch==2.4.0 --extra-index-url https://download.pytorch.org/whl/cu118
      ```

   - CPU only
      ```bash
      pip install torch==2.4.0+cpu --index-url https://download.pytorch.org/whl/cpu
      ```
### Install PyTorch extensions
```bash
pip install stm-gnn[torch-extensions]
```

### Install GUI dependencies
```bash
pip install pyqt6 pyMuPDF
```

## Quick Start
There are two ways to run the GUI.

### Using the source code
- Clone the repository or download the source code in a zip file.
   ```bash
   git clone https://github.com/tuminguyen/stm_graph_gui.git
   ```

- Navigate to the directory where you have download the GUI code.

- Run the following command:
   ```bash
   python main.py
   ```

### Using the executable file

If you prefer not to run the source code, you can download the pre-built executable files for your system. In current release version, we provide executables for Linux-based system only (recommend Ubuntu 22.04 for best compatibility). 

- Go to the [releases page](https://github.com/tuminguyen/stm_graph_gui/releases)

- Download the appropriate version for your system architecture.

- You can choose between the `CPU` or the `CUDA` version:

   - If you choose the `CPU`:
      - Download the `linux_86_64_cpu.zip`

      - Extract the `.zip` file and run the executable file directly *(in terminal or double-click)* without any installation.

   - If you choose the `CUDA`: 

      - Download all 3 parts of the executable file, named `STM-Graph-part-1`, `STM-Graph-part-2`, `STM-Graph-part-3`

      - Combine them into a single executable file using the following command on your terminal:
         ```bash
         cat STM-Graph-part-* > STM-Graph
         ```

      - Make the file executable:
         ```bash  
         chmod +x STM-Graph
         ```

      - Run the executable in the terminal with ```./STM-Graph``` or simply double-click on the file to launch the GUI.

N.B. You may need to run ```chmod +x [execution_file]``` if you face permission issues on your Linux system.

## Citation
If you find this GUI useful, please consider citing our original paper work.

```
@inproceedings{ghaffari2025stm,
  title={STM-Graph: A Python Framework for Spatio-Temporal Mapping and Graph Neural Network Predictions},
  author={Ghaffari, Amirhossein and Nguyen, Huong and Lov{\'e}n, Lauri and Gilman, Ekaterina},
  booktitle={Proceedings of the 34th ACM International Conference on Information and Knowledge Management},
  pages={6377--6381},
  year={2025}
}
```
