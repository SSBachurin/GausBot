import gzip
import shutil

class GauArc(object):
    def _compress(self, _in, _out):
        with open(_in, 'rb') as f_in:
            with gzip.open(_out, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)