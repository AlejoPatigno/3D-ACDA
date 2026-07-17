import logging

from pada3dacb.training.experiment_logging import setup_experiment_logger


def test_setup_experiment_logger_writes_utf8(tmp_path):
    log_file = tmp_path / "experiment.log"
    logger = setup_experiment_logger(
        "pada3dacb.test",
        log_file=log_file,
        level=logging.INFO,
        context={"experiment": "unit", "fold": 0, "seed": 42},
    )
    logger.info("mensaje con acento")

    text = log_file.read_text(encoding="utf-8")
    assert "mensaje con acento" in text
    assert "fold=0" in text


def test_repeated_logger_setup_does_not_duplicate_handlers(tmp_path):
    log_file = tmp_path / "experiment.log"
    logger = setup_experiment_logger("pada3dacb.repeat", log_file=log_file)
    first_count = len(logger.handlers)
    logger = setup_experiment_logger("pada3dacb.repeat", log_file=log_file)
    assert len(logger.handlers) == first_count
