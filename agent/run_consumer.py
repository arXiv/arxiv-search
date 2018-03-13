"""Execute the KCL consumer process."""

import warnings
from amazon_kclpy import kcl
from search.agent.consumer import MetadataRecordProcessor
from search.factory import create_ui_web_app


if __name__ == "__main__":
    app = create_ui_web_app()
    app.app_context().push()
    cache_dir = app.config.get('METADATA_CACHE_DIR', None)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        kcl_process = kcl.KCLProcess(
            MetadataRecordProcessor(cache_dir=cache_dir)
        )
        kcl_process.run()
