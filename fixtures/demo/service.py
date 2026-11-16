import subprocess
from config import API_TOKEN

def evaluate(value):
    return eval(value)

def invoke(command):
    return subprocess.check_output(command, shell=True)
