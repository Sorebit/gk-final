import glfw
from OpenGL.GL import *
from pyrr import matrix44 as m44, Vector3 as v3
import math

from shader import Shader
from loaded_object import LoadedObject
from light import Light


class Window:
    def __init__(self, width: int, height: int, title: str):
        # Initialize window
        if not glfw.init():
            raise Exception("GLFW cannot be initialized!")

        self._width, self._height = width, height
        self._window = glfw.create_window(width, height, title, None, None)

        if not self._window:
            glfw.terminate()
            raise Exception("Window cannot be created!")

        # Set resize handler
        glfw.set_window_size_callback(self._window, self.on_resize)
        # Set window as current context
        glfw.make_context_current(self._window)

        # Set options
        glClearColor(0.6, 0.7, 0.7, 1)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Matrices
        self._fov, self._near, self._far = None, None, None
        self._eye, self._target, self._up = None, None, None
        self.projection_matrix, self.view_matrix = None, None
        self._prepare_matrices()

        # Shaders
        self.shaders = {
            "phong": Shader("shaders/phong_vs.glsl", "shaders/phong_fs.glsl"),
            "gouraud": Shader("shaders/gouraud_vs.glsl", "shaders/gouraud_fs.glsl"),
            "light_source": Shader("shaders/light_source_vs.glsl", "shaders/light_source_fs.glsl"),
        }
        self.current_shader: Shader = None
        self.use_shader(self.shaders["gouraud"])

        self.scene = [
            LoadedObject("data/floor.obj"),
            LoadedObject("data/uv_sphere.obj", 2, 1.5, -1),
            LoadedObject("data/box/box-T2F_N3F_V3F.obj", -1, 1, -2),
            LoadedObject("data/monkey.obj", 0, 1, 1),
        ]

        self.light_obj = LoadedObject("data/box/box-V3F.obj")  # Box to represent light sources
        self.light = Light(amb=v3([0.3, 0.3, 0.3]),
                           dif=v3([1.0, 1.0, 1.0]),
                           spe=v3([1.0, 1.0, 1.0]),
                           pos=v3([1.2, 3.0, 2.0]),
                           lss=self.shaders["light_source"],
                           obj=self.light_obj)

    def use_shader(self, shader: Shader) -> None:
        self.current_shader = shader
        self.current_shader.use()
        # Update matrices after changing shader
        self.update_projection()
        self.update_view()

    def _prepare_matrices(self) -> None:
        # Projection matrix
        self._fov = 45
        self._near = 0.1
        self._far = 100
        # View matrix
        self._eye: v3 = v3([math.sin(0) * 5, 8, math.cos(0) * 10])
        self._target: v3 = v3([0, 2.0, 0])
        self._up: v3 = v3([0, 1, 0])

    def update_view(self) -> None:
        """Recalculate view matrix and upload it to shader."""
        self.view_matrix = m44.create_look_at(self._eye, self._target, self._up)
        self.current_shader.set_view(self.view_matrix)

    def update_projection(self) -> None:
        """Recalculate projection matrix and upload it to shader."""
        a = self._width / self._height
        self.projection_matrix = m44.create_perspective_projection(self._fov, a, self._near, self._far)
        self.current_shader.set_projection(self.projection_matrix)

    def on_resize(self, _window, width, height) -> None:
        self._width, self._height = width, height
        glViewport(0, 0, self._width, self._height)
        self.update_projection()

    def main_loop(self) -> None:
        # cnt = 0
        while not glfw.window_should_close(self._window):
            glfw.poll_events()

            # Clear buffers
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            # Advance objects in their movements
            self.move_objects()

            # Camera
            cam_x = math.sin(glfw.get_time() * 0.5) * 7
            cam_z = math.cos(glfw.get_time() * 0.5) * 7
            # self._eye = v3([-cam_x, 3.0, cam_z])
            # cam_front = v3([0, 0, -1])
            # self._target = self._eye + cam_front   # Front facing camera
            # self._target = v3.from_matrix44_translation(model_1)  # targeted moving camera

            # Light
            # light_color = v3([
            #     math.sin(glfw.get_time() * 2.0),
            #     math.sin(glfw.get_time() * 0.7),
            #     math.sin(glfw.get_time() * 1.3)
            # ])
            # self.light.diffuse = light_color * v3([0.5] * 3)
            # self.light.ambient = self.light.diffuse * v3([0.2] * 3)

            self.light.set_pos(v3([cam_x, 4.0, cam_z]))
            self.use_shader(self.shaders["light_source"])
            self.light.draw()

            # TODO: Handle changing shaders by keyboard shortcuts
            # Choose lighting shader
            # if cnt < 1000:
            #     self.use_shader(self.gouraud_shader)
            # else:
            self.use_shader(self.shaders["phong"])
            #   if cnt == 2000:
            #         cnt = 0
            # cnt += 1

            # TODO: Consider changing back to uploading viewPos or change Gouraud to process things in view space
            self.current_shader.set_v3("viewPos", self._eye)

            self.light.use_light(self.current_shader)
            # Draw shaded objects
            for o in self.scene:
                o.draw(self.current_shader)

            # Swap buffers
            glfw.swap_buffers(self._window)

    def move_objects(self):
        rot_x = m44.create_from_x_rotation(0.5 * glfw.get_time())
        rot_y = m44.create_from_y_rotation(0.8 * glfw.get_time())
        trans_y = math.sin(glfw.get_time())
        translation = m44.create_from_translation(v3([0, trans_y, 0]))
        rotation = m44.multiply(rot_x, rot_y)

        upside_down = m44.create_from_x_rotation(math.pi)
        model_1 = m44.multiply(upside_down, self.scene[1].pos)
        model_1 = m44.multiply(translation, model_1)
        model_1 = m44.multiply(rot_y, model_1)
        self.scene[1].model = model_1

        # self.scene[2].model = m44.multiply(rotation, self.scene[2].pos)
        self.scene[3].model = m44.multiply(rotation, self.scene[3].pos)


def main():
    window = Window(1280, 720, "GK Final")
    window.main_loop()


if __name__ == '__main__':
    main()
    glfw.terminate()
