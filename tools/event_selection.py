"""Full-map trigger selection uses its label, not an all-covering hit region."""
def covers_map(rectangle,width,height):
 x1,y1,x2,y2=rectangle
 return width>0 and height>0 and x1<=0 and y1<=0 and x2>=width-1 and y2>=height-1

def point_in_box(box,x,y):
 return box is not None and box[0]<=x<box[2] and box[1]<=y<box[3]
