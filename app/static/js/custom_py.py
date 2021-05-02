import sys

from browser import document
from browser.widgets.dialog import InfoDialog


class Redirect:
    def write(self, *args, output_id="result-code-ran", end="\n", sep=" "):
        document[output_id].textContent += sep.join(args)


redirect = Redirect()
sys.stdout = redirect
sys.stderr = redirect
