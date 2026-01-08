% ============================================================
% 本程序用于：优化“两级悬挂隔振系统”并进行【磷青铜弹簧应力校核】
% 结构：MXC盘(源) -> 3根磷青铜弹簧 -> m1(90kg) -> 1根弹簧 -> m2(2kg)
% ============================================================
function optimize_for_two_stages()
% ---- LaTeX 设置 ----
set(groot,'defaultTextInterpreter','latex','defaultLegendInterpreter','latex');

%% ---- 1. 系统常量与数据加载 ----
gain = 100; sens = 1.026; g0 = 9.80665; 
m1 = 90.0; m2 = 2.0; 
[filename, pathname] = uigetfile({'*.csv','CSV Files (*.csv)'}, 'Select MXC Data');
if isequal(filename,0), return; end
raw = readmatrix(fullfile(pathname, filename), 'NumHeaderLines', 4);
t = raw(:,1); v = raw(:,2);

% 信号处理
dt = median(diff(t)); fs = 1/dt;
a_ms2 = (v./(gain * sens)) * g0; a_ms2 = a_ms2 - mean(a_ms2);
[Sa, f] = pwelch(a_ms2, hamming(max(256, min(round(fs*10), numel(a_ms2)))), [], [], fs, 'psd');
keep = f >= 1.0; f=f(keep); Sa=Sa(keep); w=2*pi*f;

%% ---- 2. 参数优化 ----
% 变量: [k1_total, k2, z1, z2]
lb = [1000, 500, 0.01, 0.01]; ub = [1e6, 1e5, 0.4, 0.4];
toX = @(y) lb + (ub-lb).*(1./(1+exp(-y)));
toY = @(x) log((x-lb)./(ub-x));

x0 = [5e4, 5000, 0.05, 0.05];
% 确保这里的子函数名与下面定义的完全一致：internal_obj_func
objY = @(y) internal_obj_func(y, toX, m1, m2, f, w, Sa, g0);
opts = optimset('Display','off','MaxIter',5000,'TolX',1e-7);
[y_opt, ~] = fminsearch(objY, toY(x0), opts);
x_opt = toX(y_opt);

k1 = x_opt(1); k2 = x_opt(2); z1 = x_opt(3); z2 = x_opt(4);
c1 = 2*z1*sqrt(k1*m1); c2 = 2*z2*sqrt(k2*m2);

%% ---- 3. 磷青铜应力与固有频率校核 ----
% 材料属性：磷青铜
tau_allow = 200e6; % 许用剪切应力 200 MPa
G_bronze = 42e9;   % 剪切模量 42 GPa

% 第一级校核 (3根分担)
F1_single = (m1+m2)*g0/3;
k1_single = k1/3;
C = 6; n = 12; % 假定旋绕比和圈数以推算线径
d1 = (k1_single * 8 * C^3 * n / G_bronze); 
Wahl_K = (4*C-1)/(4*C-4) + 0.615/C;
tau1 = Wahl_K * (8 * F1_single * C) / (pi * d1^2);
S1 = tau_allow / tau1;

% 计算固有频率
M = [m1, 0; 0, m2]; K = [k1+k2, -k2; -k2, k2];
fn = sqrt(sort(eig(K, M))) / (2*pi);

%% ---- 4. 输出报告 ----
fprintf('\n========= 磷青铜悬挂系统优化报告 =========\n');
fprintf('系统频率: f1 = %.2f Hz, f2 = %.2f Hz\n', fn(1), fn(2));
fprintf('------------------------------------------\n');
fprintf('【第一级 (3根并联)】:\n');
fprintf('  单根目标刚度: %.2f N/mm\n', k1_single/1000);
fprintf('  推算所需线径: %.2f mm\n', d1*1000);
fprintf('  静态计算应力: %.2f MPa\n', tau1/1e6);
if S1 > 1.2
    fprintf('  承重判断: [安全] 安全系数 S = %.2f\n', S1);
else
    fprintf('  承重判断: [警告] 磷青铜强度不足！需增加线径或弹簧数量。\n');
end
fprintf('------------------------------------------\n');
fprintf('【第二级 (1根)】:\n');
fprintf('  目标刚度: %.2f N/mm\n', k2/1000);
fprintf('  阻尼比 z2: %.4f\n', z2);
fprintf('==========================================\n');

%% ---- 5. 性能绘图 ----
f_plot = logspace(0, 3, 1000);
T_plot = abs(tf_Gjw(k1,k2,c1,c2,m1,m2,1i*2*pi*f_plot));
figure('Color','w','Name','Isolation Performance');
subplot(2,1,1); semilogx(f_plot, 20*log10(T_plot), 'LineWidth', 2); grid on;
title('Displacement Transmissibility (X_2/X_0)'); ylabel('dB');
subplot(2,1,2); loglog(f, Sa/g0^2, f, (abs(tf_Gjw(k1,k2,c1,c2,m1,m2,1i*w)).^2).*Sa/g0^2, 'LineWidth', 1.5); grid on;
legend('Source (MXC)','Output (m2)'); xlabel('Frequency (Hz)'); ylabel('g^2/Hz');
end

% ============================================================
% 子函数定义区
% ============================================================

function J = internal_obj_func(y, toX, m1, m2, f, w, Sa, g0)
    x = toX(y);
    k1=x(1); k2=x(2); z1=x(3); z2=x(4);
    c1=2*z1*sqrt(k1*m1); c2=2*z2*sqrt(k2*m2);
    G = tf_Gjw(k1,k2,c1,c2,m1,m2,1i*w);
    Sa_out = (abs(G).^2).*Sa;
    
    % 优化目标：1-100Hz RMS 最小
    idx = (f >= 1) & (f <= 100);
    rms_val = sqrt(trapz(f(idx), Sa_out(idx)));
    
    % 静态拉伸约束惩罚 (防止磷青铜拉伸过长)
    d1 = (m1+m2)*g0/k1; d2 = m2*g0/k2;
    penalty = 1e8 * (max(0, d1 - 0.2)^2 + max(0, d2 - 0.15)^2);
    J = rms_val + penalty;
end

function Gjw = tf_Gjw(k1,k2,c1,c2,m1,m2,jw)
    % 悬挂串联系统传递函数
    num = (c1*jw + k1).*(c2*jw + k2);
    den = (m1*jw.^2 + (c1+c2)*jw + (k1+k2)).*(m2*jw.^2 + c2*jw + k2) - (c2*jw + k2).^2;
    Gjw = num ./ den;
end