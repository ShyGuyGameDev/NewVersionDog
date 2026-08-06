
import math

ROTRADIUS = 31.0
LTHIGH = 100.0
LCALF =  125.327

rad2deg = 180.0 / math.pi
deg2rad = math.pi / 180.0



def getangleabc( ab, bc, ca ):
    v = (ab*ab + bc*bc - ca*ca) / (2.0 * ab * bc )
    if ( v > 1 ):
        v = 1
    if ( v < -1 ):
        v = -1
    return (math.acos(v) * rad2deg)


def calcPositionXYZ(  rot_angle,
                      hip_angle,
                      knee_angle ):

        knee_angle = 180.0 - knee_angle
        #find height of knee below hip
        sa_rad = hip_angle * deg2rad
        yk = LTHIGH * math.cos( sa_rad )
        xk = LTHIGH * math.sin( sa_rad )

        #find height of foot below knee
        ak_rad = (180.0 - hip_angle - knee_angle) * deg2rad
        yf = LCALF * math.cos( ak_rad )
        xf = LCALF * math.sin( ak_rad )

        y = -yk - yf

        xz = xk - xf

        #now find x and z from xz
        #double wa_rad = waist_angle * deg2rad;
        x = xz # * cos( wa_rad);
        #z = 0; //-xz * sin( wa_rad);

        y = -y


        #this is x and y assuming leg was vertical with zero rot_angle
        #when rotator rotates, x remains the same, only y changes
        r = rot_angle * deg2rad
        z = ( ROTRADIUS * math.cos(r) ) - ( y * math.sin(r) )
        z -= ROTRADIUS #remove effect of rot_radius
        #update y
        y = y * math.cos(r) + ROTRADIUS * math.sin(r)

        return (x, y, z )

def calcAnglesXY( x, y ):
    max_length = LTHIGH + LCALF

    l = math.sqrt(x*x + y*y) #length of leg in desired  position
    if ( l > max_length ):
        l = max_length

    l_hip = getangleabc( LTHIGH, l, LCALF)

    l_angle = getangleabc( l, y, x )
    if ( x < 0 ):
        l_angle = -l_angle

    hip_angle = l_hip + l_angle

    knee_angle = 180.0 - getangleabc( LCALF, LTHIGH, l )

    h = hip_angle
    k = knee_angle

    return (h,k)


def calcAnglesXYZ( x, y, z ):
    o = ROTRADIUS
    dsq = y*y + (o+z)*(o+z)
    d = math.sqrt( dsq )

    cosa = (o+z)/d
    a = math.acos( cosa )

    cosaplusr = o / d
    aplusr = math.acos( cosaplusr )

    r = aplusr - a #in radians

    r = r * rad2deg

    r = -r

    print( "R is " , r )

    lsq = dsq - o*o
    l = math.sqrt( lsq )

    #now the 2d part
    (h,k) = calcAnglesXY( x, l )
    return (r,h,k)

#(x,y,z) = (0,150,50)

#(r,h,k) = calcAnglesXYZ(x,y,z)
#print ( r, h, k )
#print calcPositionXYZ( r, h, k )

