% 根据弹簧拉伸量 Δl 计算轴向固有频率，并绘制 f–Δl 曲线
% 公式：f = (1 / (2π)) * sqrt(g / Δl)，适用于轻质量或近似无质量弹簧模型

%% === 参数设定 ===
g = 9.81;           % 重力加速度 [m/s^2]
% m = 12.8;         % 如需考虑质量，可加入质量项（此处未使用）

%% === 拉伸量 Δl 区间 ===
l = linspace(0.01, 1, 1000);  % 伸长量 1 cm ~ 100 cm，单位[m]

%% === 轴向固有频率计算 ===
f_vertical = (1/(2*pi)) * sqrt(g ./ l);   % 固有频率 f(Δl)

%% === 绘制 f–Δl 曲线 ===
figure;
plot(l*100, f_vertical, 'b', 'LineWidth', 2);
xlabel('伸长量 \Delta l (cm)');
ylabel('轴向固有频率 f_0 (Hz)');
title('f_{0,vertical} vs \Delta l');
grid on;
ylim([0 10]);

%% === 输出整数拉伸量点的固有频率 ===
disp('Δl (cm)    f_vertical (Hz)');
for i = 1:1:100
    delta_l_i = i / 100;  % 单位 m
    f_i = (1/(2*pi)) * sqrt(g / delta_l_i);
    fprintf('%3d\t\t%8.3f\n', i, f_i);
end
