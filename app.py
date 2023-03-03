from myProject import app
from dotenv import load_dotenv

load_dotenv()

if __name__ == '__main__':    
    app.run(port=3000,debug=True)