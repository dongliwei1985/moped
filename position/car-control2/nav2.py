import time

import nav_signal
import eight
import driving
import nav_tc

from nav_log import tolog, tolog0
from nav_util import sign, dist, start_new_thread

from math import pi, cos, sin, sqrt, atan2, acos, asin, log

def checkbox1(x, y, tup, leftp):
    (lxprev, lyprev, lx, ly) = tup

    dlx = lx-lxprev
    dly = ly-lyprev
    a = atan2(dlx, dly)
    lx1 = lxprev + dlx*cos(a) - dly*sin(a)
    ly1 = lyprev + dlx*sin(a) + dly*cos(a)

    dx = x-lxprev
    dy = y-lyprev
    x1 = lxprev + dx*cos(a) - dy*sin(a)
    y1 = lyprev + dx*sin(a) + dy*cos(a)

    if y1 >= lyprev and y1 <= ly1:
        if leftp:
            if lxprev > x1:
                print("%f %f [%f %f]" % (x, y, lxprev, x1))
                nav_signal.speak("ee")
                return False
        else:
            # when leftp==False, we have really rxprev etc.
            if lxprev < x1:
                print("%f %f         [%f %f]" % (x, y, x1, lxprev))
                nav_signal.speak("oo")
                return False

    return True

def checkpos():
    pos = eight.findpos(g.ppx,g.ppy,g.ang)
    #print((g.ppx,g.ppy,g.ang),pos)


    if g.currentbox == None:
        return True
    x = g.ppx
    y = g.ppy
    # check if we are outside the lane we are supposed to be in
    stat = checkbox1(x, y, g.currentbox[0], True)
    if not stat:
        return False
    stat = checkbox1(x, y, g.currentbox[1], False)
    if not stat:
        return False

    r = None

    # Not completely correct: we don't consider the car's corners.
    carwidth = 0.30
    rside = 0.8-carwidth/2

    if g.ppx < rside:
        r = rside-(g.ppx-carwidth/2)
        wallang = -90-g.ang
    if g.ppx > 3.0-rside:
        r = rside-(3.0-g.ppx-carwidth/2)
        wallang = 90-g.ang

    if g.ppy > 19.7-rside:
        r2 = rside-(19.7-g.ppy-carwidth/2)
        wallang = 0-g.ang
        if r == None or r2 < r:
            r = r2

    # if g.can_ultra is small and r is None, we don't really know
    # what to do
    if r != None and g.can_ultra < r:
        r = g.can_ultra
        # plus a little because we measure from the front

    if r != None:
        if r > rside or r < -rside:
            print("r = %f, %f %f" % (r, g.ppx, g.ppy))
        else:
            theta = asin(r/rside)*180/pi
            wallang = wallang%360
            if wallang > 180:
                wallang -= 360
            if abs(wallang) < abs(theta):
                print("wall angle! %f %f (%f %f) %f" % (
                        wallang, theta, g.ppx, g.ppy,
                        g.can_ultra))
                return False
            else:
                pass
                #print("(wall angle %f %f)" % (wallang, theta))

    return True

def getdist(x2, y2):
    # NEW
    x1 = g.ppx
    y1 = g.ppy

    d = dist(x1, y1, x2, y2)
    tolog("we are at (%f, %f), distance to (%f, %f) is %f" % (
            x1, y1, x2, y2, d))

    return d

def goto_1(x, y):
    g.targetx = x
    g.targety = y

    missed = False
    inc = 0
    inc2 = 0
    lastdist = None
    brake_s = 0.0

    while True:
        if g.remote_control:
            print("remote_control is true")
            return 2

        if not checkpos():
            print("checkpos returned False")
            return 2

        if g.poserror:
            print("positioning system error")
            return 2

        if g.obstacle:
            print("obstacle")
            return 2

        dist = getdist(x, y)
        if g.inspeed != 0:
            # Assume we are going in the direction of the target.
            # At low speeds, braking time is about 1.5 s.
            brake_s = 1.5 * abs(g.inspeed)/100

        # say that braking distance is 1 dm at higher speed, when
        # braking electrically
        if g.inspeed > 0:
            brake_s = 0.4
        else:
            brake_s = 0.6

        # we should only use brake_s when we are going to stop
        brake_s = 0.0

        # 'lastdist' is never non-None now, nor 'missed'
        if lastdist != None:
            if dist < lastdist - 0.01:
                inc = -1
                lastdist = dist
            elif dist > lastdist + 0.01:
                if inc == -1:
                    missed = True
                    tolog("missed target")
                inc = 1
                lastdist = dist

        tolog("gotoa1 %f %f -> %f %f" % (g.ppx, g.ppy, x, y))

        a = atan2(y-g.ppy, x-g.ppx)
        adeg = 180/pi*a
        adeg = 90-adeg

        adiff = g.ang - adeg
        adiff = adiff%360

        tolog("gotoa2 a %f adeg %f adiff %f" % (a, adeg, adiff))

        if g.speedsign < 0:
            adiff += 180

        if adiff > 180:
            adiff -= 360

        adiff = -adiff
        # now, positive means the target is to the right of us

        tolog("gotoa3 adiff %f" % (adiff))

        #print(adiff)

#        if dist < g.targetdist or dist < brake_s or missed:
        if (not g.allangles and abs(adiff) > 90) or dist < g.targetdist:
            if False:
                #stop("9")
    #            driving.drive(-1)
                # continue a little so it can pass the target if it wasn't
                # there yet
                time.sleep(0.5)
    #            driving.drive(-1)
    #            time.sleep(0.2)
                driving.drive(0)
            #print("adiff %f dist %f" % (adiff, dist))
            if dist < g.targetdist:
                #print("dist < %f" % g.targetdist)
                pass
            if abs(adiff) > 90:
                print("adiff = %f; leaving (%f,%f) behind" % (adiff,x,y))
                return 1

            return 0



        asgn = sign(adiff)
        aval = abs(adiff)

        st = g.anglefactor*aval
        if st > 100:
            st = 100
        st = asgn*g.speedsign*st

        if False:
            st_d = st - g.steering
            if st_d > 10:
                st = g.steering + 10
            elif st_d < -10:
                st = g.steering - 10

        driving.steer(st)

        tolog("gotoa4 steer %f" % (st))

        if not g.simulate:
            nav_tc.send_to_ground_control("dpos %f %f %f %f 0 %f" % (
                    g.ppx,g.ppy,g.ang,time.time()-g.t0, g.finspeed))

        tt0 = time.time()
        d = eight.roaddist(g.ppx, g.ppy)

        if d > g.slightlyoffroad:
#            print("roaddist %f at %f, %f" % (d, g.ppx, g.ppy))
            if d > g.maxoffroad:
                print("roaddist %f at %f, %f" % (d, g.ppx, g.ppy))
                return 2

        tt1 = time.time()
        dtt = tt1-tt0
        dtt1 = 0.1 - dtt
        if dtt1 > 0:
            time.sleep(0.1)

def goto(x, y, state):
    start_new_thread(gotoaux, (x, y, state))

def gotoaux(x, y, state):
    print("gotoaux %f %f %s" % (x, y, state))
    driving.drive(0)
    if state == "accident":
        g.signalling = True
        start_new_thread(signal, ())

    time.sleep(4)
    driving.drive(30)
    status = nav2.goto_1(x, y)
    if status != 0:
        print("goto_1 returned %d for (%f, %f); we are at (%f, %f)" % (
                status, x, y, g.ppx, g.ppy))
        return False
    g.signalling = False
    driving.drive(0)
    return True

