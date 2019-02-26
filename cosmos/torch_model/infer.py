import click
from model.model import MMFasterRCNN
from model.utils.config_manager import ConfigManager
import torch
from inference.inference import InferenceHelper
from cosmos.torch_model.inference.data_layer.inference_loader import InferenceLoader


def run_inference(img_dir, proposal_dir, model_config,weights, out_dir):
    cfg = ConfigManager(model_config)
    model = MMFasterRCNN(cfg)
    # TODO file checking and GPU inference
    model.load_state_dict(torch.load(weights, map_location={"cuda:0": "cpu"}))
    loader = InferenceLoader(img_dir, proposal_dir, "png", cfg.CC_LAYER.WAPRED_SIZE)
    device = torch.device("cpu")
    infer_session = InferenceHelper(model, loader, device)
    infer_session.run(out_dir)




@click.command()
@click.argument("img_dir")
@click.argument("proposal_dir")
@click.argument("model_config")
@click.argument("weights")
@click.argument("dir")
def run_cli(img_dir, proposal_dir, model_config,weights, out_dir):
    run_inference(img_dir, proposal_dir, model_config,weights, out_dir)

if __name__ == "__main__":
    run_cli()
