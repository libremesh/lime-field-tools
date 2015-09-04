import kivy
kivy.require('1.9.0')

from kivy.app import App
from kivy.properties import ObjectProperty, NumericProperty, StringProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.network.urlrequest import UrlRequest

from kivy.logger import Logger

from components.initialize import InitializePlatform
from components.ttsspeak import TtsSpeak

#import netifaces

ROUND_DURATION = 5
DELAY = 1.5
PERFECT_SIGNAL = 50
DEFAULT_HOST = "minodo.info"

tts = TtsSpeak("")

class SignalMonitor(Widget):
    host = StringProperty("")
    target_stations = ListProperty([])
    signal = NumericProperty(0)
    stations_spinner = ObjectProperty(None)
    interfaces_spinner = ObjectProperty(None)
    host_input = ObjectProperty(None)
    available_interfaces = ListProperty(["wlan1-adhoc", "wlan0-adhoc"])
    quality_color = ListProperty((1, 0, 0))


    def __init__(self, *args, **kwargs):
        super(SignalMonitor, self).__init__(*args, **kwargs)
        self.stations_spinner.bind(text=self.set_target_station)
        self.interfaces_spinner.bind(text=self.set_interface)
        self.host_input.multiline = False
        self.host_input.bind(on_text_validate=self.set_host)
        self.host_input.bind(focus=self.clean_host)
        self.last_signal = 0
        self.round_iterations = 0
        self.interface = "wlan1-adhoc"
        self.target_station = None
        self.target_selected = False
        self.host = DEFAULT_HOST

    def set_target_station(self, spinner, text):
        self.target_selected = True
        self.target_station = text

    def set_interface(self, spinner, text):
        self.interface = text
        self.target_selected = False

    def clean_host(self, instance, value):
        if instance.focus:
            Clock.schedule_once(lambda dt: instance.select_all())
        else:
            Clock.schedule_once(lambda dt: instance.cancel_selection())


    def set_host(self, instance):
        if instance.text:
            self.host = instance.text
            self.target_selected = False

    def show_signal(self, req, result):
        self.signal = 0
        self.round_iterations += 1
        text = None

        # we just ignore unknown or faulty hosts for the time being
        if type(result) != type([]):
            return

        # initialize to the neighbor with best signal
        if not self.target_selected:
            best_neighbor = {"hostname": None, "signal": -100}
            self.target_stations = []
            for station in result:
                if "_" in station['station_hostname']:
                    station_hostname = station['station_hostname'][:station['station_hostname'].rfind("_")]
                else:
                    station_hostname = station['station_hostname']
                station_signal = station['attributes']['signal']
                self.target_stations.append(station_hostname)
                if station_signal > best_neighbor["signal"]:
                    best_neighbor["hostname"] = station_hostname
                    best_neighbor["signal"] = station_signal
            self.stations_spinner.text = best_neighbor["hostname"]

        else:
            for station in result:
                hostname = station['station_hostname']
                target = "%s_%s" % (self.target_station, self.interface)
                # consider the case where the hostname is not bat-hosts resolved
                if ("_" in hostname and hostname == target)\
                   or hostname == self.target_station:
                        self.signal = station['attributes']['signal'] #station_signal
            
            if self.signal:
                quality_percent = (100 + self.signal) * 100.0 / (100 - PERFECT_SIGNAL)
                quality = min(100, quality_percent ) / 100.0
                self.quality_color = (1-quality, quality, 0)
                # no matter what, if we've done a full round, say the complete number
                text = str(self.signal)[1:]
                if self.round_iterations >= ROUND_DURATION:
                    self.round_iterations = 0
                elif self.signal != self.last_signal:
                    if abs(self.signal)/10 != abs(self.last_signal)/10 or (self.signal % 10) == 0:
                        self.round_iterations = 0
                    # only speak last digit
                    else:
                        text = text[1:]
                    self.last_signal = self.signal
                else:
                    text = None

            else:
                text = "error"

            if text:
                tts.message = text
                tts.speak()
#            Logger.info(self.target_station +" "+ str(self.signal))

    def update(self, dt):
#        gws = netifaces.gateways()
#        self.host = gws['default'][netifaces.AF_INET][0]
        url = 'http://%s/cgi-bin/luci/status/json/stations/%s'\
              % (self.host, self.interface)
        UrlRequest(url, self.show_signal) #.wait()


class LiMeApp(App):

    def build(self):
        InitializePlatform()
        signal_monitor = SignalMonitor()
        Clock.schedule_interval(signal_monitor.update, DELAY)
        return signal_monitor

if __name__ == '__main__':
    LiMeApp().run()
