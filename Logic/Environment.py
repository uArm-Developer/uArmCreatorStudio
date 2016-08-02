"""
This software was designed by Alexander Thiel
Github handle: https://github.com/apockill
Email: Alex.D.Thiel@Gmail.com


The software was designed originaly for use with a robot arm, particularly uArm (Made by uFactory, ufactory.cc)
It is completely open source, so feel free to take it and use it as a base for your own projects.

If you make any cool additions, feel free to share!


License:
    This file is part of uArmCreatorStudio.
    uArmCreatorStudio is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    uArmCreatorStudio is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with uArmCreatorStudio.  If not, see <http://www.gnu.org/licenses/>.
"""
import json
from Logic        import Paths
from copy         import deepcopy
from Logic.Global import printf
from Logic.Vision import Vision
from Logic        import Video, ObjectManager, Robot, Global
__author__ = "Alexander Thiel"


class Environment:
    """
    Environment is a singleton. Do not create more than one! It is intended to help cope with the needs of GUI
    programming, where at any point I might need access to the robot, video, or settings. However, some rules apply: if
    Environment is passed to a class, do not save it to the class, instead pull what is needed from there and save
    that to the class instead.


    Environment holds the following thing and handles their shutdown:
        - VideoStream object
        - Vision object
        - Robot object
        - ObjectManager object


    THE ENVIRONMENT DOES NOT HOLD THE INTERPRETER, BY DESIGN: Since an Interpreter can run an interpreter inside of it,
    recursively, then the environment must not hold an interpreter. They are seperate. An Interpreter can hold an
    environment, however.


    Rules of thumb:
        - Objects that do not change while the interpreter is running are stored in Environment
            - Vision Objects
            - Movement Paths
        - Objects that are added and modified while interpeter is running are stored in the Interpeter
            - Variables generated by commands
            - "on the fly" vision objects generated by commands
    """

    def __init__(self, settingsPath=Paths.settings_txt):
        # Initialize Global Variables
        Global.init()

        # Load settings before any objects are created
        self.__settingsPath = settingsPath
        self.__settings     = self.__loadSettings()


        # Set up environment objects
        self.__vStream    = Video.VideoStream()           # Gets frames constantly
        self.__robot      = Robot.Robot()
        self.__vision     = Vision(self.__vStream)  # Performs computer vision tasks, using images from vStream
        self.__objectMngr = ObjectManager.ObjectManager()


        # If the settings have any information, try to instantiate objects. Otherwise, GUI will do this as user requests
        cameraID = self.__settings['cameraID']
        if cameraID is not None:
            self.__vStream.setNewCamera(cameraID)


        robotID = self.__settings['robotID']
        if robotID is not None:
            self.__robot.setUArm(robotID)





        # This keeps track of objects that have been self.addObject()'d, so self.saveObjects() actually saves them.
        # self.changedObjects = []


    # Getting System Objects
    def getRobot(self):
        return self.__robot

    def getVStream(self):
        return self.__vStream

    def getVision(self):
        return self.__vision

    def getObjectManager(self):
        return self.__objectMngr


    # Settings controls
    def getSettings(self):
        return deepcopy(self.__settings)

    def getSetting(self, category):
        return deepcopy(self.__settings[category])

    def updateSettings(self, category, newSettings):
        """
        Apply any new settings that have been changed. If they've been changed, also save the program.
        """

        current = self.__settings[category]
        # Create a quick function that will check if a setting has been changed. If it has, an action will be taken.


        # If settings change, then save the changes to the config file, and update the self.__settings dictionary
        if (current is None or not current == newSettings) and newSettings is not None:
            printf("Environment| Saving setting: ", category)

            # Update the self.__settings dictionary
            self.__settings[category] = deepcopy(newSettings)

            # Save the settings to a file
            json.dump(self.__settings, open(self.__settingsPath, 'w'),
                      sort_keys=False, indent=3, separators=(',', ': '))
        else:
            printf("Environment| No settings changed: ", category)

    def __loadSettings(self):
        """
        Load a settings file, and update the default values with the loaded values, then set that as settings.

        If the settins file could not be loaded, just return the default values.
        """
        defaultSettings = {
                            # LOGIC RELATED SETTINGS
                            "robotID":            None,  # COM port of the robot


                            "cameraID":           None,  # The # of the camera for cv to connect


                            "motionCalibrations": {
                                                    "stationaryMovement": None,
                                                    "activeMovement":     None
                                                  },


                            "coordCalibrations":  {
                                                    "ptPairs":            None,   # Pairs of (Camera, Robot) pts
                                                    "failPts":            None,   # Coordinate's where calib failed
                                                    "groundPos":          None    # The "Ground" pos, in [x,y,z]
                                                  },


                            # GUI RELATED SETTINGS
                            "consoleSettings":    {
                                                    "wordWrap":           False,  #  ConsoleWidget settings
                                                    "robot":               True,  #  What gets printed in console
                                                    "vision":              True,
                                                    "serial":             False,
                                                    "interpreter":         True,
                                                    "script":              True,
                                                    "gui":                False,
                                                    "other":               True,
                                                  },

                            "windowGeometry":       None,  # The size and shape of the main window
                            "windowState":          None,  # Location and size of dockWidgets on the mainWindow
                            "lastOpenedFile":       None   # So the GUI can open the last file you had
                          }

        # Load the settings config and set them
        printf("Environment| Loading Settings")

        # Try to load a settings file. If it fails, simply return the default settings
        try:
            def updateDictionary(default, new):
                """
                This is a custom function for updating dictionaries that have nested dictionaries. The idea is that if
                I ever change the save format for the Settings file, there won't be any corruption issues- it will
                simply input a default value for keys that aren't in the old save file, and get rid of keys that
                aren't in the new format. Compatibility is not much easier!

                It's better than dictionary.update(newdictionary), because it handles nested dictionaries and their
                values as well. Works great!
                """
                for key in default:
                    if key in new:
                        if isinstance(new[key], dict):
                            updateDictionary(default[key], new[key])
                        else:
                            default[key] = new[key]

            newSettings = json.load(open(self.__settingsPath))


            updateDictionary(defaultSettings, newSettings)

            # Replace the current settings with new settings
            return defaultSettings

        except IOError as e:
            printf("Environment| ERROR: No settings file detected. Using default values. Error:", e)
            return defaultSettings

        except ValueError as e:
            printf("Environment| ERROR: while loading an existing settings file. Using default values. Error: ", e)
            return defaultSettings



    # Close system objects
    def close(self):
        # This will try to safely shut down any objects that are capable of running threads.
        self.__robot.setExiting(True)
        self.__vision.setExiting(True)
        self.__vStream.endThread()


