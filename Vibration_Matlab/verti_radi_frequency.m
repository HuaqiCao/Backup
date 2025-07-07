% === 参数设定 ===
g = 9.81;           % 重力加速度 [m/s^2]
%m = 12.8;           % 质量 [kg]

% === 拉伸量 Δl ===
l = linspace(0.01, 1, 1000);  % 1cm 到 100cm，单位[m]

% === 轴向固有频率计算 ===
f_vertical = (1/(2*pi)) * sqrt(g ./ l);   % Δl 为弹簧伸长长度

% === 绘图 ===
figure;
plot(l*100, f_vertical, 'b', 'LineWidth', 2);
xlabel('伸长量 \Delta l (cm)');
ylabel('轴向固有频率 f_0 (Hz)');
title('f_{0,vertical} vs \Delta l');
grid on;
ylim([0 10]);

% === 输出整数点信息 ===
disp('Δl (cm)    f_vertical (Hz)');
for i = 1:1:100
    delta_l_i = i / 100;  % 单位 m
    f_i = (1/(2*pi)) * sqrt(g / delta_l_i);
    fprintf('%3d\t\t%8.3f\n', i, f_i);
end
