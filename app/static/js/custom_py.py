from browser import document
import sys

class Redirect:
    def write(self, *args, output_id='result-code-ran', end='\n', sep=' '):
        document[output_id].textContent += sep.join(args)

redirect = Redirect()
sys.stdout = redirect
sys.stderr = redirect
