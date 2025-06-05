import stm_graph
import os
import numpy as np
from utils import rasterize_process_check
from time import strftime, localtime
from datetime import timedelta

# ********** START WORKER THREAD FUNC HERE  **********
def process_task(conf):
    geo_df = stm_graph.preprocess_dataset(
        data_path= os.path.dirname(conf['data_path']),
        dataset= os.path.basename(conf['data_path']),
        time_col=conf["time_column"],
        lat_col=conf["lat_column"],
        lng_col=conf["long_column"],
        filter_dates=(conf["date_filter_start"], conf["date_filter_end"]),
        testing_mode=conf["test_mode"],
        test_bounds= conf["bounds"],
        crs=conf["input_crs"],
        visualize=True,
        fig_format="pdf",
        output_dir=conf["output_dir"],
        show_background_map=True,
        point_color="red",
        point_alpha=0.5,
        point_size=1,
        vis_crs=conf["meter_crs"],
    )
    rasterize_process_check(out_prepocess_dir=f'{conf["output_dir"]}/preprocess')
    return {"status": "ok", "data": geo_df}

def map_task(conf, mapper, geodf):
    mapping_result = mapper.create_mapping(geodf) # tuple (df, p2x)
    mapper.visualize(
        points_gdf=geodf,
        partition_gdf=mapping_result[0],
        point_to_partition=mapping_result[1],
        out_dir=conf['output_dir'],
        remove_empty=True,
        testing_mode=False,
        file_format="pdf"
    )
    rasterize_process_check(out_prepocess_dir=f'{conf["output_dir"]}/mapping')
    p2x = mapping_result[1]
    gdf_valid = geodf[p2x >= 0].copy()
    p2x_valid = p2x[p2x >= 0].copy()
    return {"status": "ok", "data": {"res": mapping_result, "geo_valid":gdf_valid, "p2x_valid": p2x_valid}}

def generate_data_task(conf, mapped_geodf, gdf_valid, p2x_valid):
    osm_features = None
    if conf["osm_types"] is not None:
        osm_features = stm_graph.extract_osm_features(
            regions_gdf=mapped_geodf,
            bounds=conf["bounds"],
            feature_types=conf["osm_types"],
            normalize=True,
            meter_crs=conf["meter_crs"],
            lat_lon_crs=conf["input_crs"]
        )
        osm_features_path = os.path.join(conf["output_dir"], "osm_features.csv")
        osm_features.to_csv(osm_features_path)
    
    graph_data = stm_graph.build_graph_and_augment(
        grid_gdf=mapped_geodf,
        points_gdf=gdf_valid,
        point_to_cell=p2x_valid,
        adj_matrix=None,
        remove_empty_nodes=True,
        out_dir=conf["output_dir"],
        save_flag=False,
        static_features=osm_features,
    )
    
    temporal_dataset, _, _ = stm_graph.create_temporal_dataset(
        edge_index=graph_data["edge_index"],
        augmented_df=graph_data["augmented_df"],
        edge_weights=graph_data["edge_weight"],
        node_ids=graph_data["node_ids"],
        static_features=osm_features,
        time_col=conf["time_column"],
        cell_col="cell_id",
        bin_type=conf["pred_type"],
        horizon=conf["horizon"],
        interval_hours=conf["interval_step"],
        history_window=conf["window_size"],
        use_time_features=conf["use_time_features"],
        task=conf["app_type"],
        downsample_factor=1,
        normalize=True,
        scaler_type="minmax",
        out_dir=conf["output_dir"],
        dataset_name=f"stmgraph_data_{strftime('%Y-%m-%d_%H%M%S', localtime())}",
        output_format="4d", 
    )    
    res = {"status": "ok", "temporal_graph_data": temporal_dataset, 
                "graph_data": graph_data,
                "num_nodes": graph_data["num_nodes"], 
                "num_edges": graph_data["edge_index"].shape[1],
                "osm_features": osm_features
    }
    if osm_features is not None:
        res["num_extracted_osm_features"] = len(osm_features.columns)
        
    return res
        
def plot_task(conf, temporal_dataset, graph_data, osm_features, mapped_geodf):
    # convert 4d to 3d
    stat_feat_count = osm_features.shape[1] if osm_features is not None else 0
    temporal_dataset_3d = stm_graph.convert_4d_to_3d_dataset(
        temporal_dataset, static_features_count=stat_feat_count
    )
    
    if conf["plot_type"] == "node":
        plot_view = conf["plot_nodes"]["View"][0]
        fig_size = (15, 8) 
        title =  "Event over time in 2D"
        if plot_view == '3d':     
            fig_size = (15, 10)
            title =  "Event over time in 3D"
        # plot time series nodes
        stm_graph.plot_node_time_series(
                temporal_dataset_3d,
                num_nodes=conf["plot_nodes"]["n_nodes"][0],
                selection_method=conf["plot_nodes"]["Selection method"][0],
                plot_type=plot_view,
                time_delta=timedelta(hours=conf["plot_nodes"]["Time delta"][0]),
                n_steps=conf["plot_nodes"]["n_step"][0],
                title=title,
                figsize=fig_size,
                file_format="pdf",
                out_dir=conf["output_dir"],
                filename=f"time_series_{plot_view}",
                rasterized=False,
                fig_dpi=300,
        )
    elif conf["plot_type"] == "spatial":
        time_step = conf["plot_spatial"]['Time step'][0]
        node_counts = np.array(
            [
                temporal_dataset_3d.features[time_step][node, 0].item()
                for node in range(graph_data["num_nodes"])
            ]
        )
        # plot spatial network with region and edge colors
        stm_graph.plot_spatial_network(
            regions_gdf=mapped_geodf,
            edge_index=graph_data["edge_index"],
            edge_weights=graph_data["edge_weight"],
            node_values=node_counts,
            node_ids=graph_data["node_ids"],
            time_step=time_step,
            title="Event Density (Time step: {timestep})",
            out_dir=conf["output_dir"],
            filename="spatial_network",
            file_format="pdf",
            rasterized=False,
            fig_dpi=300,
        )
    else: #conf["plot_type"] == "heatmap"
        # plot temporal heatmap -->  patterns across time and nodes
        stm_graph.plot_temporal_heatmap(
            temporal_dataset_3d,
            selection_method=conf['plot_heatmap']['Selection method'][0],
            num_nodes=conf['plot_heatmap']['n_nodes'][0],
            n_steps=conf['plot_heatmap']['n_step'][0],
            time_delta=timedelta(hours=conf['plot_heatmap']['Time delta'][0]),
            title="Events Temporal Heatmap",
            figsize=(14, 7),
            out_dir=conf["output_dir"],
            filename="temporal_heatmap",
            file_format="pdf",
            rasterized=False,
            fig_dpi=300,
        )

def create_model_task(conf):
    selected_model = conf["training"]["model"]
    conf["training"][selected_model].keys()
    model_kwargs = {}
    for _, (k, v) in enumerate(conf["training"][selected_model].items()):
        model_kwargs[k] = v[0]
    model = stm_graph.create_model(
            model_name=selected_model,
            source="custom",
            task=conf["app_type"],
            **model_kwargs
    )
    return {"status": "ok", "model": model}

def training_task(conf, model, temporal_dataset):
    fixed_batch_size = False
    if conf["training"]["model"] == "agcrn":
        fixed_batch_size = True
    results = stm_graph.train_model(
        model=model, 
        dataset=temporal_dataset, 
        optimizer_name=conf["training"]["optimizer"], 
        learning_rate=conf["training"]["learning_rate"], 
        weight_decay=conf["training"]["weight_decay"],
        momentum=conf["training"]["momentum"], 
        task=conf["app_type"], 
        num_epochs=conf["training"]["num_epochs"],  
        batch_size=conf["training"]["batch_size"], 
        test_size=conf["training"]["test_ratio"], 
        val_size=conf["training"]["val_ratio"], 
        early_stopping=conf["training"]["early_stopping"], 
        patience=conf["training"]["es_patience"], 
        scheduler_type=conf["training"]["scheduler_type"], 
        lr_decay_epochs=conf["training"]["lr_step_decay"], 
        lr_decay_factor=conf["training"]["lr_decay_factor"], 
        lr_patience=conf["training"]["lr_patience"],
        wandb_api_key=conf["training"]["wandb_api_key"], 
        wandb_project=conf["training"]["wandb_project"], 
        experiment_name=conf["training"]["experiment_name"], 
        use_wandb=conf["training"]["use_wandb"], 
        log_dir=conf["training"]["log_dir"],
        fixed_batch_size=fixed_batch_size
    )
    return {"status": "ok", "training_results": results}

# ********** END WORKER THREAD FUNC HERE  **********
        