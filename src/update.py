
# State : pending | posted | archive | rejected
IMAGE_BORDER = 10
TEXTURE_WIDTH = 4096
TEXTURE_HEIGHT = 4096
CALENDAR_WIDTH = 1600 + 20
CALENDAR_HEIGHT = 1600 + 20
POSTER_WIDTH = 594 + 20
POSTER_HEIGHT = 841 + 20




import urllib.request
import numpy as np
import cv2


def SetImage(texture, path, pos, size = None, border = 10):
   
    img = cv2.imread(path)
    print(img.shape)
    # Add padding to image with black color
    img = cv2.copyMakeBorder(img, border, border, border, border, cv2.BORDER_CONSTANT, value=[0, 0, 0])
    if size != None:
        img = cv2.resize(img, size)
    print(img.shape)
    h, w, _ = img.shape
    # print(h, w)
    texture[pos[1]:pos[1]+h, pos[0]:pos[0]+w, :3] = img
    return texture

import urllib.request as req   


class _Log:
    def __init__(self):
        self.str = ""

    def Append(self, str, end="\n"):
        print(str)
        self.str += str + end

Log = _Log()

def PosterUpdate(texture, url, path, position):
    try:
        print("Retriving image from "+ url + " to " + path)
        cursor = position
        cal_path = path
        urllib.request.urlretrieve(url, cal_path)
        texture = SetImage(texture, cal_path, cursor, (POSTER_WIDTH, POSTER_HEIGHT))
        return texture
    except Exception as e:
        Log.Append("Poster Update Failed : " + str(e))

if __name__ == "__main__":
    # Opener
    opener=urllib.request.build_opener()
    opener.addheaders=[('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'),
       ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
       ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.3'),
       ('Accept-Encoding', 'none'),
       ('Accept-Language', 'en-US,en;q=0.8'),
       ('Connection', 'keep-alive')]
    # opener.addheaders=[('User-Agent','Chrome/95.0.4638.54')]
    urllib.request.install_opener(opener)

    Log.Append("Updating Calendar and Posters...")

    texture = np.zeros((TEXTURE_WIDTH, TEXTURE_HEIGHT,3), np.uint8)
    # Load Web Poster, Calendar
    try:
        cal_path = "./imgs/calendar.png"
        urllib.request.urlretrieve("https://drive.google.com/uc?export=download&id=1EmWoThq0wxXHIJDKwKfPk7JY1WBM7eUA", cal_path)
        texture = SetImage(texture, cal_path,(0, 0) ,(CALENDAR_WIDTH, CALENDAR_HEIGHT))
    except Exception as e:
        Log.Append("Calendar Update Failed : " + str(e))

    cursor = (0, CALENDAR_HEIGHT)
    texture = PosterUpdate(texture, "http://drive.google.com/uc?export=view&id=1-i4MkB7KHVKhiwxYm10ntcIN673rQnBd"
            ,"./imgs/poster1.png" ,cursor)

    cursor = (cursor[0]+POSTER_WIDTH, cursor[1])
    texture = PosterUpdate(texture, "http://drive.google.com/uc?export=view&id=1uNI4CnPMJCde--VePjTmcZjYkJSOgKsD"
            ,"./imgs/poster2.png" ,cursor)

    cursor = (cursor[0]+POSTER_WIDTH, cursor[1])
    texture = PosterUpdate(texture, "http://drive.google.com/uc?export=view&id=1kOjay3PY1KPXLdplno1h_-PQXi1UjKJl"
            ,"./imgs/poster3.png" ,cursor)

    cursor = (cursor[0]+POSTER_WIDTH, cursor[1])
    texture = PosterUpdate(texture, "http://drive.google.com/uc?export=view&id=1Wiy4LkO65mYIgFx8XLlcvtHCDoabTxZ8"
            ,"./imgs/poster4.png" ,cursor)

    cursor = (cursor[0]+POSTER_WIDTH, cursor[1])
    texture = PosterUpdate(texture, "http://drive.google.com/uc?export=view&id=1TfVQ13D_4EgJmiM7hHEM1rpS4LL5viqN"
            ,"./imgs/poster5.png" ,cursor)

    cursor = (cursor[0]+POSTER_WIDTH, cursor[1])
    texture = PosterUpdate(texture, "http://drive.google.com/uc?export=view&id=1vd03IHIGYUeebPaZd3mo7ggjObYGCOXK"
            ,"./imgs/poster6.png" ,cursor)





    cursor = (0, CALENDAR_HEIGHT+POSTER_HEIGHT)
    texture = PosterUpdate(texture, "http://drive.google.com/uc?export=view&id=1jxdi_GTvdIldhGfYnGczYqyAKv8Rfp3M"
            ,"./imgs/fixedposter1.png" ,cursor)

    cursor = (cursor[0]+POSTER_WIDTH, CALENDAR_HEIGHT+POSTER_HEIGHT)
    texture = PosterUpdate(texture, "http://drive.google.com/uc?export=view&id=1B9CCM6oB0DHTdijU1QQjcqM1SdIWMz7q"
            ,"./imgs/fixedposter2.png" ,cursor)
    
    cursor = (cursor[0]+POSTER_WIDTH, CALENDAR_HEIGHT+POSTER_HEIGHT)
    texture = PosterUpdate(texture, "http://www.dropbox.com/s/ucv3hvxnvodrp25/PS1.png?dl=1"
            ,"./imgs/fixedposter3.png" ,cursor)
    
    cursor = (cursor[0]+POSTER_WIDTH, CALENDAR_HEIGHT+POSTER_HEIGHT)
    texture = PosterUpdate(texture, "https://drive.google.com/uc?export=view&id=13eyIrp3bnONXD7biKsc5HlkPVk4MgRfH"
            ,"./imgs/fixedposter4.png" ,cursor)
    
    cursor = (cursor[0]+POSTER_WIDTH, CALENDAR_HEIGHT+POSTER_HEIGHT)
    texture = PosterUpdate(texture, "http://drive.google.com/uc?export=view&id=1EZQb26Y20HjV1ztTmyjPWEsmPCa0lyzv"
            ,"./imgs/fixedposter5.png" ,cursor)
    # Write video
    cv2.imwrite('./poster.png',texture)   
    
    out = cv2.VideoWriter('./poster.mp4',0x7634706d, 15, (TEXTURE_WIDTH, TEXTURE_HEIGHT))
    out.write(texture)
    out.release()
    cv2.imwrite('./calendar.png',texture[:CALENDAR_WIDTH,:CALENDAR_HEIGHT])   
    out2 = cv2.VideoWriter('./calendar.mp4',0x7634706d, 15, (CALENDAR_WIDTH, CALENDAR_HEIGHT))
    out2.write(texture[:CALENDAR_WIDTH,:CALENDAR_HEIGHT])
    out2.release()
