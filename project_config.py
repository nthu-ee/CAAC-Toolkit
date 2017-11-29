import os


class project_config():

    __script_dir__ = os.path.dirname(os.path.abspath(__file__))

    projectRootDir = __script_dir__
    dataDir = projectRootDir + '/data'
    resultDir = dataDir + '/crawler_{}'
