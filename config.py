CONFIG = {
    'output_dir': None,
    'data_path': None,
    'time_column': None, 
    'lat_column': None, 
    'long_column': None, 
    'input_crs': 'EPSG:4326', 
    'meter_crs': 'EPSG:3857',
    'test_mode': False, # ---- preprocess and general
    'bounds': {
        "min_lat": 40.4774,  # Southern boundary
        "max_lat": 40.9176,  # Northern boundary
        "min_lon": -74.2591,  # Western boundary
        "max_lon": -73.7004,  # Eastern boundary
    },
    'use_time_features': True,
    'app_type': 'classification',
    'pred_type': 'daily',
    'horizon': 1,
    'window_size': 1,
    'interval_step': 1, 
    'date_filter_start': None,
    'date_filter_end': None,
    'osm_types': None,
    'mapping': 'grid', # ---- mapping
    'cell_size': 1000,
    'vor_small_cell_size': 1000,
    'vor_big_cell_size': 2000,
    'adm_shape_file': None,
    'plot_type': 'node', # ---- temporal data plot
    'plot_nodes': {
        'View': ['2d', 'Plot view in 2D or 3D'],
        'Selection method': ['random', 'Method to select nodes'],
        'Time delta': [1, 'Time delta between steps'], 
        'n_nodes': [5, 'Number of nodes to plot'], 
        'n_step': [None, "Number of time steps to include"],
    },
    'plot_spatial': {
        'Time step': [None, 'Optional time step for temporal data'],
    },
    'plot_heatmap':{
        'Selection method': ['random', 'Method to select nodes'],
        'Time delta': [1, 'Time delta between steps'],
        'n_nodes': [5, 'Number of nodes to plot'], 
        'n_step': [None, "Number of timesteps to include"],
    },
    'training': { # model params 
        "model": "gcn",
        "gcn": {
            "hidden_channels": [64, "Size of hidden layers"], 
            "dropout": [0.2, "Dropout rate (float)"],
            "in_channels": [1, "Number of input features"],
            "out_channels": [1, "Number of output features"],
            "temporal_pooling": ["last", "Method to pool temporal dimension"]
        },
        "tgcn": {
            "batch_size": [1, "Size of the batch"],
            "in_channels": [1, "Number of input features"],
            "out_channels": [1, "Number of output features"],
        },
        "stgcn": {
            "hidden_channels": [64, "Size of hidden layers"], 
            "dropout": [0.0, "Dropout rate (float)"],
            "num_st_blocks": [2, "Number of ST-Conv blocks"],
            "in_channels": [1, "Number of input features"],
            "out_channels": [1, "Number of output features"],
            "kernel_size": [3, "Size of temporal convolution kernel, should be same as window size"],
            "K": [3, "Order of Chebyshev polynomials, should be same as window size"],
            "num_nodes": [1, "Number of nodes in the graph"],
            "history_window": [3, "Number of time steps in history, should be same as window size"]
        },
        "dcrnn": {
            "hidden_dim": [64, "Size of hidden layers"], 
            "dropout": [0.0, "Dropout rate (float)"],
            "in_channels": [1, "Number of input features"],
            "out_channels": [1, "Number of output features"],
            "K": [3, "Kernel size, should be same as window size"]
        },
        "agcrn": {
            "hidden_dim": [64, "Size of hidden layers"], 
            "embedding_dim": [8, "Number of node embedding dimensions"],
            "in_channels": [1, "Number of input features"],            
            "out_channels": [1, "Number of output features"],
            "num_nodes": [1, "Number of nodes in the graph"],
            "k": [3, "Kernel size, should be same as window size"],
        },
        "graph_data_path": '',
        "optimizer": "adam",
        "learning_rate": 0.001,
        "weight_decay": 0.0,  
        "momentum": 0.9,
        "scheduler_type": "step",
        "lr_step_decay": 2, # for scheduler-step
        "lr_decay_factor": 0.1,
        "lr_patience": 2,
        "test_ratio": 0.15,
        "val_ratio": 0.15,
        "num_epochs": 10,
        "early_stopping": False,
        "es_patience": 50,
        "batch_size": 8,
        "wandb_api_key": None,
        "wandb_project": 'stm_graph',
        "experiment_name": "stm_graph_experiment",
        "use_wandb": False,
        "log_dir": '',
    }
}