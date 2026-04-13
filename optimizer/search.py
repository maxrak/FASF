from utils import sample_params
from config import PARAM_BOUNDS


def random_search():
    return sample_params(PARAM_BOUNDS)