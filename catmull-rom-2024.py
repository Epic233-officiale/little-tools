import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseEvent

def multiply_matrix(a, b):
    rows_a, cols_a = len(a), len(a[0])
    rows_b, cols_b = len(b), len(b[0])
    if cols_a != rows_b:
        return None
    result = [[0 for _ in range(cols_b)] for _ in range(rows_a)]
    for i in range(rows_a):
        for j in range(cols_b):
            for k in range(cols_a):
                result[i][j] += a[i][k] * b[k][j]
    return result

def matrix_P(t, points):
    M = [[-0.5, 1.5,-1.5, 0.5],
         [ 1.0,-2.5, 2.0,-0.5],
         [-0.5, 0.0, 0.5, 0.0],
         [ 0.0, 1.0, 0.0, 0.0]]
    G = [[point[0]] for point in points]
    G_y = [[point[1]] for point in points]
    T = [[t**3, t**2, t, 1]]
    result_x = multiply_matrix(multiply_matrix(T, M), G)
    result_y = multiply_matrix(multiply_matrix(T, M), G_y)
    return result_x[0][0], result_y[0][0]

def CRSpline(t, points):
    if len(points) < 4:
        return None
    else:
        for i in range(len(points) - 3):
            segment_points = points[i:i + 4]
            if t < i + 1 and t >= i:
                x, y = matrix_P(t - i, segment_points)
                return x, y
        return None

points = [(0, 0), (0.5, 1), (2, -1), (3, 0)]

def update_plot():
    t_values = [i / 100 for i in range(0, (len(points) - 3) * 100 + 1)]
    curve = [CRSpline(t, points) for t in t_values]
    curve = [p for p in curve if p is not None]
    x_points, y_points = zip(*points)
    plt.clf() 
    plt.plot(x_points, y_points, 'ro')
    if curve:
        x_curve, y_curve = zip(*curve)
        plt.plot(x_curve, y_curve, 'b-')
    plt.draw()

fig, ax = plt.subplots()
update_plot()
fig.canvas.manager.window.setWindowTitle("Centripetal Catmull-Rom Spline")
dragging_point = None

def on_click(event: MouseEvent):
    global dragging_point
    if event.dblclick:
        clicked_x, clicked_y = event.xdata, event.ydata
        if clicked_x is not None and clicked_y is not None:
            threshold = 0.1
            for i, (x, y) in enumerate(points):
                if abs(x - clicked_x) < threshold and abs(y - clicked_y) < threshold and len(points)>4:
                    del points[i]
                    update_plot()
                    return
            points.append((clicked_x, clicked_y))
            update_plot()
    elif event.button == 1:
        clicked_x, clicked_y = event.xdata, event.ydata
        if clicked_x is not None and clicked_y is not None:
            threshold = 0.1
            for i, (x, y) in enumerate(points):
                if abs(x - clicked_x) < threshold and abs(y - clicked_y) < threshold:
                    dragging_point = i
                    return

def on_motion(event: MouseEvent):
    global dragging_point
    if dragging_point is not None:
        new_x, new_y = event.xdata, event.ydata
        if new_x is not None and new_y is not None:
            points[dragging_point] = (new_x, new_y)
            update_plot()

def on_release(event: MouseEvent):
    global dragging_point
    if dragging_point is not None:
        dragging_point = None

fig.canvas.mpl_connect('button_press_event', on_click)
fig.canvas.mpl_connect('motion_notify_event', on_motion)
fig.canvas.mpl_connect('button_release_event', on_release)
plt.show()
