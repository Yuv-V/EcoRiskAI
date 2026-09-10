"""Run the EcoRiskAI v1 local MVP pipeline."""

from src.dataset.clean_dataset import run_clean_dataset
from src.dataset.merge_yearly_exports import run_merge_yearly_exports
from src.models.predict import run_prediction
from src.models.predict_landscape import run_landscape_prediction
from src.models.train import run_training
from src.utils.config import load_config
from src.utils.logger import setup_logger


def main() -> None:
    """Merge exports, clean features, train the model, and generate predictions."""
    logger = setup_logger(__name__)
    config = load_config()

    logger.info("Starting EcoRiskAI v1 local MVP pipeline.")

    if run_merge_yearly_exports(config) is None:
        logger.error("Pipeline stopped during yearly export merge.")
        return

    if run_clean_dataset(config) is None:
        logger.error("Pipeline stopped during dataset cleaning.")
        return

    model_path = run_training(config)
    if model_path is None:
        logger.warning("XGBoost training did not complete. Prediction will use heuristic MVP risk.")

    if run_prediction(config) is None:
        logger.error("Pipeline stopped during prediction generation.")
        return

    # Optional wall-to-wall scoring. No-op until a full-grid export is provided.
    run_landscape_prediction(config)

    logger.info("EcoRiskAI pipeline completed successfully.")


if __name__ == "__main__":
    main()
