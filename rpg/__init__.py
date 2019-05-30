"""
A module for making and displaying drifting gratings to the 
screen of a raspberry pi (with the default NOOBS installation
of raspbian) while bypassing the windowing system.

It is best to run this module from the fullscreen terminal,
accessed with Ctrl+Alt+F1 (Ctrl+Alt+F7 returns to the desktop)
because otherwise the X windowing system and this module will
both be attempting to configure the framebuffer.

This module is an object-oriented wrapper for the 
_rpigratings module, which is implemented in C for 
performance.

"""
import time as t
import os, sys, random
import RPi.GPIO as GPIO
from collections import namedtuple
from select import select

GratPerfRec = namedtuple("GratingPerformanceRecord",["fastest_frame","slowest_frame","start_time"])

#Users should edit the variable TRIGGER_PIN to the number of the pin they have conntected
#a 3.3V signal to.
TRIGGER_PIN = 5


GRAY = (127,127,127)
BLACK = (0,0,0)
WHITE = (255,255,255)
SINE = 1
SQUARE = 0

import _rpigratings as rpigratings

def build_grating(filename,spac_freq,temp_freq,
                  angle=0, resolution = (1280,720),
                  waveform = SQUARE, percent_diameter = 0,
                  percent_center_left = 0, percent_center_top = 0,
                  percent_padding = 0, verbose=True):
    """
    Create a raw animation file of a drifting grating called filename.
    The grating's angle of propogation is measured counterclockwise
      from the x-axis and defaults to zero.
    The spacial frequency of the grating is in cycles per degree of
      visual angle.
    The temporal frequency is in cycles per second.
    The resolution paramater is formatted as (width, height) and
      must match the resolution of any Screen object used to display
      the grating.
    Waveform can be 0 for a squarewave, or 1 for a sinewave. Constants 
      SQUARE and SINE are available for this purpose. Squarewaves are
      the default.
    Percent_diameter determines how much of the screen should be
      filled by the grating and how much by midgray. Setting to 0 produces
      full screen gratings.
    Percent_center_left is the center of the grating from the left edge of
      screen. Only has an effect if the grating is not full screen, i.e.
      percent_diameter > 0. 50 produces a horizontally centered grating.
    Percent_center_top is the center of the grating from the top edge of the
      screen. Only has an effect if the grating is not full screen, i.e.
      percent_diameter > 0. 50 produces a vertically centered grating.
    Percent_padding is the % of the radius used to fade the grating towards
      midgray. Setting to 0 produces a hard edged circular grating. Only has
      an effect if percent_diameter > 0.
    For smooth propogation of the grating, the pixels-per-frame speed
      is truncated to the nearest interger; low resolutions combined with
      a low temporal frequency:spacial frequency ratio may result in incorrect
      speeds of propogation or even static, unmoving gratings. This also means
      that the temp_freq is approximate only.
    """
    if percent_diameter<0:
        raise ValueError("percent_diameter param set to invalid value of %d, must be in [0,100]"
                         %percent_diameter)

    filename = os.path.expanduser(filename)
    rpigratings.draw_grating(filename,angle,spac_freq,temp_freq,
                     resolution[0],resolution[1],waveform,
                     percent_diameter, percent_center_left,
                     percent_center_top, percent_padding, verbose)


def build_list_of_gratings(list_of_angles, path_to_directory, spac_freq,
			   temp_freq, resolution = (1280,720), waveform = SQUARE,
                           percent_diameter = 0, percent_center_left = 0,
                           percent_center_top = 0, percent_padding = 0, verbose = True):

	"""
	Builds a list of gratings with the same properties but varied angles
	"""

	if len(list_of_angles) != len(set(list_of_angles)):
		raise ValueError("list_of_angles must not contain duplicate elements")


	path_to_directory = os.path.expanduser(path_to_directory)
	cwd = os.getcwd()
	os.makedirs(path_to_directory)
	os.chdir(path_to_directory)
	for angle in list_of_angles:
		build_grating(str(angle), spac_freq, temp_freq, angle, resolution, waveform,
                              percent_diameter, percent_center_left, percent_center_top,
                              percent_padding, verbose)
	os.chdir(cwd)

def convert_raw(filename, new_filename, n_frames, width, height, fps):
	filename = os.path.expanduser(filename)
	new_filename = os.path.expanduser(new_filename)

	rpigratings.convertraw(filename, new_filename, n_frames, width, height, fps)


class Screen:
    def __init__(self, resolution=(1280,720)):
        """
        A class encapsulating the raspberry pi's framebuffer,
          with methods to display drifting gratings and solid colors to
          the screen.
          
        ONLY ONE INSTANCE OF THIS OBJECT SHOULD EXIST AT ANY ONE TIME.
          Otherwise both objects will be attempting to manipulate the memory
          assosiated with the linux framebuffer. If a resolution change is desired
          first clean up the old instance of this class with the close() method
          and then create the new instance, or del the first instance.
          
        The resolution of this screen object does NOT need to match the actual
          resolution of the physical display; the linux framebuffer device is
          automatically scaled up to fit the physical display.
          
        The resolution of this object MUST match the resolution of any
          grating animation files created by draw_grating; if the resolution
          of the animation is smaller pixels will simply be misaligned, but
          if the animation is larger then attempting to play it will cause a
          segmentation fault.
        
        :param resolution: a tuple of the desired width of the display
          resolution as (width, height). Defaults to (1280,720).
         """
        self.capsule = rpigratings.init(resolution[0],resolution[1])

    def load_grating(self,filename):
        """
        Load a raw grating file called filename into local memory. Once loaded
        in this way, display_grating() can be called to display the loaded file
        to the screen.
        """
        filename = os.path.expanduser(filename)
        return Grating(self,filename)

    def load_raw(self, filename):
        filename = os.path.expanduser(filename)
        return Raw(self, filename)

    def display_grating(self, grating):
        """
        Display the currently loaded grating (grating files are created with
        the draw_grating function and loaded with the Screen.load_grating
        method). Also automatically unloads the currently loaded grating
        after displaying it unless cleanup is set to False.

        Returns a namedtuple (from the collections module) with the fields
        mean_FPS, slowest_frame_FPS,
        and start_time; these refer respectively to the average FPS, the inverse
        of the time of the slowest frame, and the time the
        grating began to play (in Unix Time).
        """
        rawtuple = rpigratings.display_grating(self.capsule, grating.capsule)
        return GratPerfRec(*rawtuple)

    def display_raw(self, raw):
        rawtuple = rpigratings.display_raw(self.capsule, raw.capsule)
        return GratPerfRec(*rawtuple)

    def display_color(self,color):
        """
        Fill the screen with a solid color until something else is
                displayed to the screen. Calling display_color(GRAY) will
                display mid-gray.
        :param color: 3-tuple of the rgb color value eg (255,0,0) for red.
                Available macros are WHITE, BLACK, and GRAY.
        :rtype None:
        """
        for value in color:
            if (value<0 or value>255):
                self.close()
                raise ValueError("Color must be a tuple of RBG values"
                                 + "each between 0 and 255.")
        rpigratings.display_color(self.capsule,color[0],color[1],color[2])

    def display_gratings_randomly(self, dir_containing_gratings, path_of_log_file="rpglog.txt"):
        """
        For each file in directory dir_containing_gratings, attempt to display
        that file as a grating. The order of display is randomised. The location
        of the log file is given by path_of_log_file, and defaults to the
        highest level directory. Gratings are seperated by one second of midgray.
        """

        dir_containing_gratings = os.path.expanduser(dir_containing_gratings)
        path_of_log_file = os.path.expanduser(path_of_log_file)
        cwd = os.getcwd()

        os.chdir(dir_containing_gratings)
        gratings = []
        for file in os.listdir():
            gratings.append((self.load_grating(file),dir_containing_gratings + "/" + file))
        random.shuffle(gratings)
        record = []
        for grating in gratings:
            perf = self.display_grating(grating[0])
            self.display_color(GRAY)
            record.append("Grating: %s \t Displayed starting at (unix time): %d \t Fastest frame (FPS): %.2f \t slowest frame (FPS): %.2f \n" 
                           %(grating[1],perf.start_time,perf.fastest_frame,perf.slowest_frame))
            t.sleep(1)
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        with open(path_of_log_file, "a") as file:
            file.writelines(record)

        os.chdir(cwd)

    def display_raw_on_pulse(self, filename, path_of_log_file="rpglog.txt"):

        filename = os.path.expanduser(filename)
        path_of_log_file = os.path.expanduser(path_of_log_file)
        self.display_color(GRAY)
        raw = self.load_raw(filename)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(TRIGGER_PIN, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
        GPIO.add_event_detect(TRIGGER_PIN, GPIO.RISING, bouncetime = 5)

        print("Waiting for pulse on pin " + str(TRIGGER_PIN) + ".")
        print("Press Enter to quit waiting...")
        while True:
            t.sleep(0.001)
            if GPIO.event_detected(5):
                perf = self.display_raw(raw)
                self.display_color(GRAY)
                with open(path_of_log_file, "a") as file:
                    file.write("Raw: %s \t Displayed starting at (unix time): %d \t Fastest frame (FPS): %.2f \t slowest frame (FPS): %.2f \n" 
                                %(filename,perf.start_time,perf.fastest_frame,perf.slowest_frame))
            if select([sys.stdin],[],[],0)[0]: #if user presses enter
                break

        GPIO.cleanup()
        print("Waiting for pulses ended")


    def display_rand_grating_on_pulse(self, dir_containing_gratings, path_of_log_file="rpglog.txt"):
        """
        Upon receiving a 3.3V pulse (NOT 5V!!!), choose a grating at
        random from dir_containing_gratings and display it. Each
        grating in the directory is guaranteed to be displayed once
        before any grating is displayed for the second time, and so on.
        When not displaying gratings the screen will be filled
        by midgray.
        """
 
        self.display_color(GRAY)
        #Load all the files in dir into a list along with their names
        dir_containing_gratings = os.path.expanduser(dir_containing_gratings)
        path_of_log_file = os.path.expanduser(path_of_log_file)
        os.chdir(dir_containing_gratings)
        gratings = []
        for file in os.listdir():
            gratings.append((self.load_grating(file),dir_containing_gratings + "/" + file))
        #Create a copy of that list to hold gratings that
        #haven't been displayed yet
        #This is a shallow copy, so it shouldn't double up
        #on memory space
        remaining_gratings = gratings.copy()
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(TRIGGER_PIN, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
        GPIO.add_event_detect(TRIGGER_PIN, GPIO.RISING, bouncetime = 5)

        print("Waiting for pulse on pin " + str(TRIGGER_PIN) + ".")
        print("Press Enter to quit waiting...")
        while True:
            t.sleep(0.001)
            if GPIO.event_detected(5):
                #Get a random index in remaining_gratings
                index = random.randint(0,len(remaining_gratings)-1)
                #display that grating
                perf = self.display_grating(remaining_gratings[index][0])
                #display mid-gray
                self.display_color(GRAY)
                #log the event to file
                with open(path_of_log_file, "a") as file:
                    file.write("Grating: %s \t Displayed starting at (unix time): %d \t Fastest frame (FPS): %.2f \t slowest frame (FPS): %.2f \n" 
                                %(remaining_gratings[index][1],perf.start_time,perf.fastest_frame,perf.slowest_frame))
                remaining_gratings.pop(index)
                if len(remaining_gratings) == 0:
                    remaining_gratings = gratings.copy()

            if select([sys.stdin],[],[],0)[0]: #if user presses enter
                break

        GPIO.cleanup()
        print("Waiting for pulses ended")

    def close(self):
        """
        Destroy this object, cleaning up its memory and restoring previous
        screen settings.
        :rtype None:
        """
        print("Screen object has been closed. You will need to make a new one")
        rpigratings.close_display(self.capsule)
        del self

    def __del__(self):
        self.close()



class Grating:
	def __init__(self, master, filename):
		if type(master).__name__ != "Screen":
			raise ValueError("master must be a Screen instance")
		self.master = master
		self.capsule = rpigratings.load_grating(master.capsule,filename)
	def __del__(self):
		rpigratings.unload_grating(self.capsule)


class Raw:
	def __init__(self, master, filename):
		if type(master).__name__ != "Screen":
			raise ValueError("master must be a Screen instance")
		self.master = master
		self.capsule = rpigratings.load_raw(filename)
	def __del__(self):
		rpigratings.unload_raw(self.capsule)
