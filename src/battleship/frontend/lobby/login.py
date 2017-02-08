import urwid
import asyncio

from .lobby import Lobby
from common.GameController import GameController
from client.lobby import ClientLobbyController
from common.states import ClientConnectionState
from common.errorHandler.BattleshipError import BattleshipError
from common.constants import ErrorCode


class LoginPopUpDialog(urwid.WidgetWrap):
    """A dialog that appears with nothing but a close button """
    signals = ['close']

    def __init__(self):
        close_button = urwid.Button("close")
        urwid.connect_signal(close_button, 'click', self.reenter_username)
        pile = urwid.Pile([urwid.Text("Sorry mate empty usernames are not allowed"), close_button])
        fill = urwid.Filler(pile)
        self.__super.__init__(urwid.AttrWrap(fill, 'popbg'))

    def reenter_username(self, foo):
        self._emit("close")


class LoginButtonWithAPopUp(urwid.PopUpLauncher):
    def __init__(self):
        # self.show = show
        #self.create_pop_up()
        self.__super.__init__(urwid.Button(""))
        urwid.connect_signal(self.original_widget, 'click',
                             lambda button: self.open_pop_up())
        # if self.show == "empty":
        #     self.open_pop_up()

    def callback_for_popup(self):
        self.open_pop_up()

    def create_pop_up(self):
        pop_up = LoginPopUpDialog()
        urwid.connect_signal(pop_up, 'close',
                             lambda button: self.close_pop_up())
        return pop_up

    def get_pop_up_parameters(self):
        return {'left': 0, 'top': 1, 'overlay_width': 32, 'overlay_height': 7}


class Login:
    def __init__(self, game_controller, lobby_controller, loop):
        self.game_controller = game_controller
        self.lobby_controller = lobby_controller
        self.loop = loop
        self.username = urwid.Edit("username: ")
        self.server_ip = urwid.Edit("Server: ", "127.0.0.1")
        self.server_port = urwid.Edit("Port: ", "8080")
        self.popup = LoginButtonWithAPopUp()

    def forward_lobby(self, key):
        if key == 'enter':
            login_task = self.loop.create_task(self.lobby_controller.try_login(self.username.get_edit_text()))
            login_task.add_done_callback(self.login_result)

    def login_result(self, future):
        # check if there is an error message to display
        e = future.exception()
        if type(e) is BattleshipError:
            if e.error_code == ErrorCode.PARAMETER_INVALID_USERNAME:
                # TODO: popup
                self.popup.callback_for_popup()
                #print("username cannot be empty")
            elif e.error_code == ErrorCode.PARAMETER_USERNAME_ALREADY_EXISTS:
                # TODO: popup
                print("username already exists")
        # and check if we are really logged in
        elif not self.lobby_controller.state == ClientConnectionState.NOT_CONNECTED:
            # ok, we are logged in
            raise urwid.ExitMainLoop()
        else:
            # TODO: popup
            print("some other weird login error")

    def login_main(self):
        dialog = urwid.Columns([
                    urwid.Text(""),
                    urwid.LineBox(urwid.Pile([self.popup, self.username, urwid.Text(""), self.server_ip, self.server_port]), 'Login'),
                    urwid.Text(""),
                    ], 2)
        f = urwid.Filler(dialog)

        urwid.MainLoop(f, [('popbg', 'white', 'dark blue')], unhandled_input=self.forward_lobby,
                       event_loop=urwid.AsyncioEventLoop(loop=self.loop), pop_ups=True).run()
