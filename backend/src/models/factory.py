from langchain.chat_models import BaseChatModel
from src.config import get_app_config
from src.reflection import resolve_class


def create_chat_model(name: str | None = None, thinking_enabled: bool = False, **kwargs) -> BaseChatModel:
    """Create a chat model instance from the config.

    Args:
        name: The name of the model to create. If None, the first model in the config will be used.

    Returns:
        A chat model instance.
    """
    config = get_app_config()
    if name is None:
        if not config.models:
            raise ValueError("No models configured in config.yaml")
        name = config.models[0].name

    model_config = config.get_model_config(name)
    if model_config is None:
        raise ValueError(f"Model {name} not found in config") from None

    # FALLBACK FOR DEPLOYMENT VERIFICATION: Use a mock if no API key is set
    import os
    is_blablador = "blablador" in model_config.name or (model_config.base_url and "blablador" in model_config.base_url)
    if is_blablador and not os.environ.get("BLABLADOR_API_KEY") and model_config.api_key == "$BLABLADOR_API_KEY":
        from langchain_community.chat_models import FakeListChatModel
        return FakeListChatModel(responses=["Hello! I am a DeerFlow agent running in a Hugging Face Space. To enable real LLM responses, please set the BLABLADOR_API_KEY secret in the Space settings."])

    model_class = resolve_class(model_config.use, BaseChatModel)

    model_settings_from_config = model_config.model_dump(
        exclude_none=True,
        exclude={
            "use",
            "name",
            "display_name",
            "description",
            "supports_thinking",
            "when_thinking_enabled",
            "supports_vision",
        },
    )

    # Standardize base URL field names for different LangChain versions and providers
    base_url = model_settings_from_config.get("base_url") or model_settings_from_config.get("api_base") or model_settings_from_config.get("openai_api_base")

    if base_url:
        # Use base_url as the primary one and remove others to avoid unexpected keyword arguments
        model_settings_from_config["base_url"] = base_url
        model_settings_from_config.pop("api_base", None)
        model_settings_from_config.pop("openai_api_base", None)

    if thinking_enabled and model_config.when_thinking_enabled is not None:
        if not model_config.supports_thinking:
            raise ValueError(f"Model {name} does not support thinking. Set `supports_thinking` to true in the `config.yaml` to enable thinking.") from None
        model_settings_from_config.update(model_config.when_thinking_enabled)

    model_instance = model_class(**kwargs, **model_settings_from_config)
    return model_instance
