import torch
from transformers import UMT5EncoderModel
from diffusers import AutoencoderKLWan, WanVACEPipeline, WanVACETransformer3DModel, GGUFQuantizationConfig
from diffusers.schedulers.scheduling_unipc_multistep import UniPCMultistepScheduler
from diffusers.utils import export_to_video

model_path = "https://huggingface.co/calcuis/wan-gguf/blob/main/wan2.1-v5-vace-1.3b-q4_0.gguf"
transformer = WanVACETransformer3DModel.from_single_file(
    model_path,
    quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
    torch_dtype=torch.bfloat16,
    )

text_encoder = UMT5EncoderModel.from_pretrained(
    "chatpig/umt5xxl-encoder-gguf",
    gguf_file="umt5xxl-encoder-q4_0.gguf",
    torch_dtype=torch.bfloat16,
    )

vae = AutoencoderKLWan.from_pretrained(
    "callgg/wan-decoder",
    subfolder="vae",
    torch_dtype=torch.float32
    )

pipe = WanVACEPipeline.from_pretrained(
    "callgg/wan-decoder",
    transformer=transformer,
    text_encoder=text_encoder,
    vae=vae, 
    torch_dtype=torch.bfloat16
)

flow_shift = 3.0
pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config, flow_shift=flow_shift)
pipe.enable_model_cpu_offload()
pipe.vae.enable_tiling()

prompt = "a pig moving quickly in a beautiful winter scenery nature trees sunset tracking camera"
negative_prompt = "blurry ugly bad"

output = pipe(
    prompt=prompt,
    negative_prompt=negative_prompt,
    width=256,
    height=256,
    num_frames=2,
    num_inference_steps=8,
    guidance_scale=2.5,
    conditioning_scale=0.0,
    generator=torch.Generator().manual_seed(0),
).frames[0]
export_to_video(output, "output.mp4", fps=8)
