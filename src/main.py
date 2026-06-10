import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import uvicorn
if __name__ == "__main__":
    uvicorn.run("src.core.app:app", host="0.0.0.0", port=5000, reload=True)