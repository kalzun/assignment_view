from browser import document
from browser.widgets.dialog import InfoDialog
import sys

class Redirect:
    def write(self, *args, output_id='result-code-ran', end='\n', sep=' '):
        document[output_id].textContent += sep.join(args)

def find_all_inputs(ev):
    '''
    Find the python code submission
    Find all the inputfunctions
    '''
    sub_code = document['submissioncode']
    InfoDialog('Output', "yes")

# document['find_input'].bind('click', find_all_inputs)


redirect = Redirect()
sys.stdout = redirect
sys.stderr = redirect
