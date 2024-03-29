''' Conditioned by o

Common usage: Action.do(s, (ta,to))
- See function docs

Actions applied on scene (Scene.py -> Scene()).
Checks for semantic validity.

Note: common_sense_proba variable is just experimental and not used now.
It should represent action feasibility probability.
E.g. object is graspable by 20% and pourable by 80%.
Then the total probability is 0.2 * 0.8 = 0.16 -> 16%
If probability is below some threshold, the action is considered not doable.
'''
import numpy as np
import itertools

class Actions():
    ''' Static Params '''
    #A = ['move_up', 'open', 'put', 'pour', 'close', 'pick_up']
    A = ['move_up', 'move_left', 'move_down', 'move_right', 'put', 'put_on', 'pour', 'pick_up', 'place', 'open', 'close']
    ## Moves -> might be changed or will be subset of actions A
    A_move = ['move_back','move_right','move_up','move_front','move_left','move_down']
    A_move_directions = [[1,0,0], [0,1,0], [0,0,1],  [-1,0,0], [0,-1,0], [0,0,-1]]

    @staticmethod
    def is_action_from_move_category(action):
        if action in Actions.A_move:
            return True
        else:
            return False

    @staticmethod
    def step(s, s2, action, ignore_location=True, out=False):
        next_state = s.copy()
        action_executed = Actions.do(next_state, action, ignore_location=ignore_location, out=out)

        reward = next_state == s2
        done = False
        if reward == True: done = True

        return next_state, reward, done, action_executed

    @staticmethod
    def get_possible_actions_bool_array(s, ignore_location=False):
        possible_actions = np.zeros([len(Actions.A), len(s.O)], dtype=bool)
        for n,a in enumerate(Actions.A):
            for m,o in enumerate(s.O):
                s2 = s.copy()
                if Actions.do(s2, (a, o), ignore_location=ignore_location):
                    possible_actions[n,m] = True
        return possible_actions

    @staticmethod
    def get_possible_actions(s, ignore_location=False, p=0.9):
        possible_actions = []
        for a in Actions.A:
            for o in s.O:
                s2 = s.copy()
                if Actions.do(s2, (a, o), ignore_location=ignore_location, p=p):
                    possible_actions.append((a,o))
        return possible_actions

    @staticmethod
    def get_possible_move_actions(s, ignore_location=False):
        possible_actions = []
        for a in Actions.A_move:
            s2 = s.copy()
            if Actions.do(s2, (a, None), ignore_location=ignore_location):
                possible_actions.append(a)
        return possible_actions

    @staticmethod
    def get_random_action():
        return np.random.choice(Actions.A)

    @staticmethod
    def get_random_possible_action(s, ignore_location=False, p=0.9):
        TaTos = Actions.get_possible_actions(s, ignore_location=ignore_location, p=p)
        if TaTos == []: return False
        return TaTos[np.random.randint(len(TaTos))]

    @staticmethod
    def get_action(id):
        return Actions.A[id]

    @staticmethod
    def get_valid_actions(s):
        valid_actions = []
        for action in Actions.A:
            for object in s.O:
                s_ = s.copy()
                r = Actions.do(s_, (action, object))
                if r:
                    valid_actions.append((action,object))

    @staticmethod
    def do(s, action, ignore_location=True, out=False, p=0.9, handle_location=False, fake_handle_location=False):
        ''' Main method
        Parameters:
            s (Scene): Scene
            a (Tuple):
                0 : Action
                1 : Object name
            ignore_location (bool): Doesn't check the eef position to target obj
            handle_location (bool): Execute sequence of actions to get the eef to the target
            fake_handle_location (bool): Assigns the target position
            out (bool): Prints on the screen
        '''
        if isinstance(action, dict):
            action = (action['target_action'], action['target_object'])

        if isinstance(action[1], str):
            o = getattr(s, action[1])
        elif action[1] is None:
            o = None
        else:
            o = action[1]

        if not Actions.is_action_from_move_category(action[0]) and fake_handle_location:
            Actions.fake_move(s, o.position)
        if not Actions.is_action_from_move_category(action[0]) and handle_location:
            move_action_seq = s.plan_path_to_position(o.position, Actions)
            Actions.execute_path_to_position(s, move_action_seq)
            if out: print(f"Executed move actions: {move_action_seq}")

        ret = getattr(Actions, action[0])(s, o, p, ignore_location=ignore_location)
        if not ret:
            if out: print("Action cannot be performed!")
            return False
        if out: print(f'{action} done!')
        return True

    @staticmethod
    def sequence_of_actions(self):
        pass

    @staticmethod
    def A_exec():
        return ['move_upCup1', 'move_upCup2', 'openDrawer', 'moveFrontCup1', 'moveFrontCup2', 'pourCup1', 'pourCup2', 'closeDrawer', 'MoveBackCup1', 'MoveBackCup2']

    ''' Action definitions
    '''
    @staticmethod
    def place(s, o=None, p=None, ignore_location=False):
        common_sense_proba = 1.
        if not s.r.attached: return False

        new_position = Actions.find_free_location(s, s.r.eef_position[0:2])

        if common_sense_proba < p: return False
        s.r.attached.position = new_position
        s.r.eef_position = new_position
        s.r.attached = None
        return True

    @staticmethod
    def find_free_location(s, center, max_rad=3):
        for r in range(max_rad+1):
            new_position = Actions.find_free_location_for_radius(s, center, r)
            if new_position is not None: return new_position

        s.info
        raise Exception("Couldn't found new place where to push!")

    @staticmethod
    def find_free_location_for_radius(s, center, radius=1):
        a = list(range(-radius, radius+1))

        directions = [p for p in itertools.product(a, repeat=2)]
        locations = np.array(directions) + center

        for location in locations:
            location_3d = np.hstack([location, np.array(0)])
            if s.collision_free_position(location_3d):
                if s.in_scene(location_3d):
                    return location_3d
        return None


    @staticmethod
    def put(s, o, p, ignore_location=False):
        if o is None: return False
        common_sense_proba = 1.

        if not ignore_location and sum(abs(s.r.eef_position_real - o.position_real)) > 1: return False
        if not s.r.attached: return False
        if o.type == 'drawer':
            if not o.opened: return False
            #if not s.r.attached.gripper_move(o.position): return False
            if common_sense_proba < p: return False
            if not o.put_in(s.r.attached): return False
        else:
            #if not s.r.attached.gripper_move(o.position): return False
            if common_sense_proba < p: return False
            if not o.stack(s.r.attached): return False
        s.r.attached = None

        return True

    @staticmethod
    def put_on(s, o, p, ignore_location=False):
        if o is None: return False
        common_sense_proba = 1.

        if not ignore_location and sum(abs(s.r.eef_position_real - o.position_real)) > 1: return False
        if not s.r.attached: return False
        if o.type == 'cup':
            return False # cup is unstackable
        #if not s.r.attached.gripper_move(o.position): return False
        if common_sense_proba < p: return False
        if not o.stack(s.r.attached): return False
        s.r.attached = None

        return True

    @staticmethod
    def replace(s, o, p, ignore_location=False):
        if o is None: return False
        ''' High level task
        '''
        return False
        raise NotImplementedError("not implemented feature for more objects")

        if not isinstance(o, (list, tuple, np.ndarray)):
            raise Exception("replace method gets only one object!")
        if not (len(o) == 2):
            raise Exception("replace method gets different number of objects!")

        o1, o2 = o

        if not o1.graspable: return False
        if not o2.graspable: return False
        if s.r.attached is not None: return False
        if not o1.on_top: return False
        if not o2.on_top: return False
        if o1.inside_drawer: return False
        if o2.inside_drawer: return False

        if not ignore_location: return False # High level task
        o1.position_real, o2.position_real = o2.position_real, o1.positon_real
        return True

    @staticmethod
    def pour(s, o, p, ignore_location=False):
        if o is None: return False
        common_sense_proba = 1.
        common_sense_proba *= o.pourable
        if not s.r.attached: return False
        #if not s.r.attached.full: common_sense_proba *= 0.2
        #if o.full: common_sense_proba *= 0.2

        if common_sense_proba < p: return False
        ''' TODO '''
        #if not s.r.attached.empty(): return False
        if not o.fill(): return False

        if not ignore_location and sum(abs(s.r.eef_position_real - o.position_real)) > 1: return False

        return True

    @staticmethod
    def pick_up(s, o, p, ignore_location=False):
        if o is None: return False
        common_sense_proba = 1.
        if not o.graspable: return False
        if s.r.attached is not None: return False
        if not o.on_top: return False
        if o.inside_drawer: return False

        if common_sense_proba < p: return False
        if not ignore_location and sum(abs(s.r.eef_position_real - o.position_real)) > 1: return False

        o.unstack()
        s.r.attached = o
        s.r.eef_position_real = o.position_real
        return True

    @staticmethod
    def open(s, o, p, ignore_location=False):
        if o is None: return False
        common_sense_proba = 1.
        if o.type != 'drawer': return False
        if o.opened: common_sense_proba *= 0.2
        '''
        >>> import numpy as np
        >>> x = np.arange(1,50)
        >>> y = 1-x*0.01 if x<50 else 0.8
        >>> import matplotlib.pyplot as plt
        >>> plt.plot(y)
        '''
        common_sense_proba *= 1-o.open_close_count*0.01 if o.open_close_count<50 else 0.8
        if common_sense_proba < p: return False
        if not ignore_location and sum(abs(s.r.eef_position_real - o.position_real)) > 1: return False

        o.open()
        return True

    @staticmethod
    def close(s, o, p, ignore_location=False):
        if o is None: return False
        common_sense_proba = 1.
        if o.type != 'drawer': return False
        if not o.opened: common_sense_proba *= 0.2

        common_sense_proba *= 1-o.open_close_count*0.01 if o.open_close_count<50 else 0.8
        if common_sense_proba < p: return False
        if not ignore_location and sum(abs(s.r.eef_position_real - o.position_real)) > 1: return False

        o.close()
        return True
    @staticmethod
    def push(s, o, p, ignore_location=False):
        if o is None: return False
        common_sense_proba = 1.
        if not o.pushable: return False

        if not ignore_location and sum(abs(s.r.eef_position_real - o.position_real)) > 1: return False
        i = 0
        while True:
            new_position = np.int64(o.position_real + np.hstack([np.random.choice(3, 2) - 1, 0]))
            if s.collision_free_position(new_position):
                if s.in_scene(new_position):
                    break
            i += 1
            if i > 10000:
                return False
                raise Exception("Couldn't found new place where to push!")

        if common_sense_proba < p: return False
        if not o.push_move(new_position): return False

        return True

    @staticmethod
    def move_back(s, o=None, p=None, ignore_location=False):
        return Actions._move_by_direction(s, np.array([1, 0, 0]))
    @staticmethod
    def move_right(s, o=None, p=None, ignore_location=False):
        return Actions._move_by_direction(s, np.array([0, 1, 0]))
    @staticmethod
    def move_up(s, o=None, p=None, ignore_location=False):
        return Actions._move_by_direction(s, np.array([0, 0, 1]))
    @staticmethod
    def move_front(s, o=None, p=None, ignore_location=False):
        return Actions._move_by_direction(s, np.array([-1, 0, 0]))
    @staticmethod
    def move_left(s, o=None, p=None, ignore_location=False):
        return Actions._move_by_direction(s, np.array([0,-1, 0]))
    @staticmethod
    def move_down(s, o=None, p=None, ignore_location=False):
        return Actions._move_by_direction(s, np.array([0, 0,-1]))
    '''
    @staticmethod
    def open_gripper(self):
        gripper_opened_before = self.gripper_opened
        self.gripper_opened = True
        if gripper_opened_before:
            return False
        else:
            return True
    @staticmethod
    def close_gripper(self):
        gripper_opened_before = self.gripper_opened
        self.gripper_opened = False
        if gripper_opened_before:
            return True
        else:
            return False
    '''
    @staticmethod
    def rotate(s, o=None, p=None, ignore_location=False):
        return True

    @staticmethod
    def _move_by_direction(s, direction):
        if s.in_scene(s.r.eef_position + direction):
            s.r.eef_position = s.r.eef_position + direction
            if s.r.attached:
                s.r.attached.position = s.r.eef_position
            return True
        else:
            return False

    @staticmethod
    def execute_path_to_position(s, plan):
        for action in plan:
            if not Actions.do(s, (action, None)):
                print("Plan cannot be executed")
                return False
        return True

    @staticmethod
    def fake_move(s, position):
        if s.in_scene(position):
            s.r.eef_position = position
            if s.r.attached:
                s.r.attached.position = s.r.eef_position
            return True
        else:
            return False

def actions_tester():
    ''' in tests folder becaused of dependency on other libraries '''
    pass
