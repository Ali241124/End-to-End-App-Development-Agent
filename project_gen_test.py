import sys, traceback, json
sys.path.append('c:/Users/ah627/OneDrive/Documents/End-to-End-App-Development-Agent')
try:
    import app.generators.project_generator as pg
    print('Import succeeded')
    # Print version info maybe
except Exception as e:
    traceback.print_exc()

