# IMPORTS
import os, time, copy, shapefile, numpy as np
from math import floor
from osgeo import gdal
from tkinter import filedialog
from tkinter import *



# FUNCTIONS
# STEP_1
# File and folder management
def getMainDir():
    print ("\n\nPlease select the folder containing the input data: \n")
    #Pause for a while to let the reader read the above line
    time.sleep(3)
    #Select the input directory
    root = Tk()
    root.withdraw()
    input_data_folder = filedialog.askdirectory()
    worksp = os.path.dirname(input_data_folder)
    return worksp



# Create a subdirectory if required
def createSubdir(worksp, subdir):
    if not os.path.isdir(worksp + "/" + subdir):
        os.mkdir(worksp + "/" + subdir)
    return worksp + "/" + subdir



# Get the complete file paths
def getInFilePaths():
    inRiversPath = worksp + "/Step1_InputData/Shapefile/"
    inGridpath = worksp + "/Step1_InputData/DEM/"
    rivers3D = worksp + "/Step2_Rivers3D/"
    correctedRiversIn3D = worksp + "/Step3_CorrectedRivers3D/"
    return inRiversPath, inGridpath, rivers3D, correctedRiversIn3D



# Check if files exist
def checkExistence(pathList):
    check = True
    for data in pathList:
        if not os.path.isfile(data):
            check = False
            break
    return check


# STEP_2
# From 2D to 3D conversion
# Get the z-values from DEM/grid
# Reference for this function
# https://gis.stackexchange.com/questions/46893/getting-pixel-value-of-gdal-raster-under-ogr-point-without-numpy#comment428498_46898
def getz (river2D):
    pts = river2D.points
    riverIn3D = []
    #Open the raster grid, get transformatios and first band
    dem = gdal.Open(inGrid) 
    forward_trs = dem.GetGeoTransform()
    reverse_trs = gdal.InvGeoTransform(forward_trs)
    band = dem.GetRasterBand(1)
    
    for i in range (len(pts)):
        
        x = river2D.points[i][0]
        y = river2D.points[i][1]
        #Convert from map to pixel coordinates.
        px, py = gdal.ApplyGeoTransform(reverse_trs, x, y)
        px = floor(px) #x pixel
        py = floor(py) #y pixel

        intval = band.ReadAsArray(px,py,1,1)
        z = intval[0][0] #Intval is a numpy array, length=1 as only 1 pixel value is needed
        riverIn3D.append([x,y,z])
    return riverIn3D





# Get the x,y values from input 2D rivers file and elevation values 
# From DEM into the 3D rivers shapefile
def from2Dto3D(shpFile):

    #Read the input file
    rivers2D = shapefile.Reader(shpFile)
    
    #Create another directory for step_2
    step2Dir = "Step2_Rivers3D"
    directory = createSubdir (worksp,step2Dir)

    #Create a new file of type POLYLINEZ
    rivers3D = shapefile.Writer(directory + '/Rivers_3D', shapeType = shapefile.POLYLINEZ )
    rivers3D.fields = rivers2D.fields[ : ]
    #Go through all the records / rivers 
    for river in rivers2D.iterShapeRecords():
        riverIn3D = getz(river.shape)
        rivers3D.linez([riverIn3D])
        rivers3D.record(*river.record)
    rivers3D.close()


# STEP_3
# Splitting, marking of flags and correction of flag segments
# This function will split a river into correct and flag segments.
def splitToSegments (river):
    #A new river dictionary will hold the river segments
    #The keys for flag sements will go like f1, f2, f3, and for correct segments c1, c2, c3
    #Whereas the value will be a list containing the 3D-coordinates of the vertices
    n_river = {}
    #The coordinate values will be collected in correct and flag segments and the add to
    # n_river dictionary defined above
    c_seg = [] #A correct segment list to hold the correct segments of a river
    f_seg = [] #A flag segment list to hold the flag segments

    #Count the number of flag and correct segments to use as keys
    flag_segments = 0
    correct_segments = 0

    #Currect lowest is the last correct point, we will start from first point and will
    # mark this as the current lowest or last correct point
    c_lowest = river.z[0]
    #Now iterate throught the a particular river points and spit river into flag and ccorrect segments
    points = river.points
    total_points = len(points)
    length_Rvr = total_points - 1

    #For first point of every river
    #If the next point is lowest then the first point/segment it is a
    # correct segment otherwise it is flag segment
    if(river.z[1] < c_lowest):
        c_seg.append([river.points[0][0],river.points[0][1],river.z[0]])
    else:
        f_seg.append([river.points[0][0],river.points[0][1],river.z[0]])

            
    #For all other points of a river
    for i in range (1, total_points):
        #Get the three coordinates of the point
        x = river.points[i][0]
        y = river.points[i][1]
        z = river.z[i]
        #Now check if the elevation of currect point is less than previous lowest value
        if(z < c_lowest):
            c_lowest = z #Now this will be the current lowest / last correct
            #Now as we detected a correct value we will check if
            # we were adding the previous values to a flag segment of a correct segment
            f_length = len (f_seg)
            #If we were adding values to a flag segment then
            if(f_length>0):
                f_seg.append([x,y,z])
                #Finish the flag segment by adding it to the n_river dictionary
                flag_segments = flag_segments + 1
                n_river['f' + str(flag_segments)] = copy.deepcopy(f_seg)
                #Empty the flag segment
                f_seg.clear()
                #Now if this was not the last point then also start the next segement
                if(i != length_Rvr):
                   if(river.z[(i+1)] < c_lowest):
                    c_seg.append([x,y,z])
                   else:
                    f_seg.append([x,y,z])
            else: #If we were adding previous values to a correct segment and this is the last point then
                if (i == length_Rvr): #add the value to a correct segment and end the process
                    c_seg.append([x,y,z])
                    correct_segments = correct_segments + 1
                    n_river['c' + str(correct_segments)] = copy.deepcopy(c_seg)
                    c_seg.clear()                       
                elif(river.z[(i+1)] < c_lowest):
                    c_seg.append([x,y,z])
                else:
                    #Finish the correct segment because the next value is again higher and
                    # A new flag segment will began
                    c_seg.append([x,y,z])
                    correct_segments = correct_segments + 1
                    n_river['c' + str(correct_segments)] = copy.deepcopy(c_seg)
                    c_seg.clear()
                    #Start a new flag segment
                    f_seg.append([x,y,z])

        #Now if the current z-values is not smaller than the previous correct / lower values
        else: #Check if this is the last point
            if(i != length_Rvr):
                f_seg.append([x,y,z])
            #if it is
            else: 
                #z = c_lowest - 1
                z = c_lowest - 1
                f_length = len (f_seg) #If we were adding values to a flag segment
                if (f_length > 0):
                    f_seg.append([x,y,z])
                    flag_segments = flag_segments + 1
                    n_river['f' + str(flag_segments)] = copy.deepcopy(f_seg)
                    f_seg.clear()
                else:
                    c_seg.append([x,y,z])
                    correct_segments = correct_segments + 1
                    n_river['c' + str(correct_segments)] = copy.deepcopy(c_seg)
                    c_seg.clear()
                      
    return n_river
    



#This fucntion will get the flag segment and will interpolate the values between the end values
# As the first and the last value is correct thus the inbetween values will be interpolated
def interpolateFlagSegments (valueOnly):
    segment = valueOnly
    length_Seg = len(segment)
    interpolatedSegment = []
    # First elevation value of the flag segment
    # Last elevation value of the segment
    # and length of the falg segment is provided to 'linspace' to interpolate
    #  the middle values to enforce the downstream flow in a river
    interpolatedArray = np.linspace (segment[0][2],segment[(length_Seg -1)][2],length_Seg)
    list(interpolatedArray) #convert to a list
    #Reference for the line of code below:
    # https://stackoverflow.com/questions/5326112/how-to-round-each-item-in-a-list-of-floats-to-2-decimal-places
    formatted_list = [ '%.2f' % elem for elem in interpolatedArray ] #format the list to only 2 decimals
    for i in range (length_Seg):
        x = float(segment[i][0])
        y = float(segment[i][1])
        z = float(formatted_list[i])
        interpolatedSegment.append([x,y,z])

    return interpolatedSegment
        
        
    
#This function is for enforcing the down stream flow.
# It will use two more functions i.e. splitToSegments and interpolateFlagSegments for
#  splitting the river into correct and falg segments and then interpolating the flag segments respectively
def correctRivers (riversIn3D):
    #Read the river file in 3D
    rivers3D = shapefile.Reader(riversIn3D) 

    #Create another directory for step_3
    step3Dir = "Step3_CorrectedRivers3D"
    directory = createSubdir (worksp,step3Dir)

    #Create a new file of type POLYLINEZ which will hold the new corrected river segments
    corrected_Rivers = shapefile.Writer(directory + '/Corrected_Rivers_3D', shapeType = shapefile.POLYLINEZ )
    corrected_Rivers.fields = rivers3D.fields[ : ] #Add all the filed from input file
    #Add a new boolean filed = 'Flag' which will be '1' for flag segment and '0' for already correct segment
    corrected_Rivers.field('Flag', 'L')
    #Now go through all the records / rivers
    for river in rivers3D.iterShapeRecords():
        riverInSegments = splitToSegments(river.shape) #Here the river will be splited into segments correct and flag
        for key, value in riverInSegments.items(): # Now iterate throught all the segmenst of one river
            if (key[0] == 'f'): #If the segment is falg segment then send this sengment to another function for correction
                interplated_River = interpolateFlagSegments(value) #This will provide the interpolated/corrected segment
                corrected_Rivers.linez([interplated_River]) #Write shape to the new shapefile
                corrected_Rivers.record(*river.record,1) #All the attributes form input and addition flag as 1 because we corrected this segment
            else:
                corrected_Rivers.linez([value])
                corrected_Rivers.record(*river.record,0)

                
    rivers3D.close()
    
#STEP_4    
#Visualization of one river for comparison
#This function will display one river hypothetically named as 'River A' in sample data before and after the correction
def compare(riverBefore,riverAfter):
    new_river =[]
    i=1
    before = shapefile.Reader(riverBefore)
    print('\n\nBELOW ARE ELEVATION VALUES OF ONE RIVER BEFORE AND AFTER FOR COMPARISON')
    print('\nElevation Values Before: ')
    print(before.shapes()[0].z) #First River in the file before
    after = shapefile.Reader(riverAfter)
    for river in after.iterShapeRecords():
        if(river.record[1] == 'River A' and river.record[2] == 1):
            print ('\nFlag Segment After Correction: ')
            print(river.shape.z)
            if (i==1):
                new_river.append(river.shape.z)
                i=2
            else:
                new_river.append(river.shape.z[1:])
        elif(river.record[1] == 'River A' and river.record[2] == 0):
            print ('\nAlready Correct Segment: ')
            print(river.shape.z)
            if (i==1):
                new_river.append(river.shape.z)
                i=2
            else:
                new_river.append(river.shape.z[1:])

    print('\n\nOVERALL RIVER BEFORE: ')
    print(before.shapes()[0].z)
    print('AFTER: ')
    #Reference for the lien below:
    #  https://stackoverflow.com/questions/952914/how-to-make-a-flat-list-out-of-a-list-of-lists
    flat_list = [item for sublist in new_river for item in sublist] #Make a flat list from list of lists
    print(flat_list)
    

    
                    
                            
                        

#Start of main
if __name__ == '__main__':

    #Start time
    start = time.time()

    
    #STEP_1 file and folder management
    # get the paths to the file and specify the file names
    #  file names are hardcoded but instead of selecting the main
    #   directory the user can be asked to select the files directly
    worksp = getMainDir()
    
    print('STEP_1 : Setting the input files paths')
    inRiversPath, inGridPath, riversIn3D,correctedRiversIn3D = getInFilePaths()

    #Get the filenames of the input files from their respective folders
    for file in os.listdir(inRiversPath):
        if file.endswith(".shp"):
            inRivers = str (os.path.join(inRiversPath,file))
    for file in os.listdir(inGridPath):
        if file.endswith(".tif"):
            inGrid = str (os.path.join(inGridPath,file))

    #Hardcoded names for the 3D files
    rivers3D = riversIn3D + 'Rivers_3D.shp'
    correctedRiversIn3D = correctedRiversIn3D + 'Corrected_Rivers_3D.shp'

    #Check if input files exist
    if not checkExistence([inRivers, inGrid]):
        print('\n\n !  One or more input file(s) not found under the given paths ! \n\n')
        raise ValueError


    #STEP_2 from 2D to 3D conversion
    # Create an new 3D Rivers file with coordinates of vertices from input river file
    #  and z-values from DEM /grid
    print('STEP_2 : Converting a 2D file to 3D file')
    from2Dto3D(inRivers)



    #STEP_3 splitting, marking of flags and correction of flag segments
    #Split the rivers into correct and flag segments and interpolate the flag segments
    print('STEP_3 : Splitting, marking flag segments and correcting the rivers')
    correctRivers(rivers3D)

    #STEP_4
    #Just to display the comparison of one river
    compare(rivers3D, correctedRiversIn3D)


    #End time
    end = time.time()
    print('\n\n\nCompleted in ' + str( round((end-start),2) ) + 's.')
