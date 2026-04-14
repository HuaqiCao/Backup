clear; clc;

%% 目标无量纲参数
delta_hat_target = 0.5;      % δ̂ = δ / sqrt(a^2 + h1^2) -> (δ_target)
a_hat_target     = 0.755;    % â = a / sqrt(a^2 + h1^2) ->（h1_target）
alpha_target     = 0.942;    % α = k1/k2 (遍历k1->K2)
alpha1_target    = 0.501;    % α₁ = k3/k2 (K2->K3)
gamma_target     = 2.143;    % γ = h/d

fprintf('目标无量纲参数:\n');
fprintf('  δ̂ = %.3f, â = %.3f, α = %.3f, α₁ = %.3f, γ = %.3f\n\n', ...
    delta_hat_target, a_hat_target, alpha_target, alpha1_target, gamma_target);

%% 铜屏蔽内径 12cm
a_target = 0.06;     %m

%% 根据 â = a / sqrt(a^2 + h1^2) 反求 h1
h1_target = sqrt(a_target^2 * (1/a_hat_target^2 - 1));

fprintf('根据 â = %.3f 和 a_target = %.3f mm 计算得到: h₁_target = %.3f mm\n\n', ...
    a_hat_target, a_target*1000, h1_target*1000);

%% 根据 δ̂ = δ / sqrt(a^2 + h1^2) 求 δ
% δ = δ̂ * sqrt(a^2 + h1_target^2)
delta_target = delta_hat_target * sqrt(a_target^2 + h1_target^2);

%% 斜弹簧原始长度（三根弹簧原长相同）
L1 = sqrt(a_target^2 + h1_target^2) + delta_target;
fprintf('根据 δ̂ = %.3f, a_target = %.3f mm, h1_target = %.3f mm 计算得到: L1 = %.3f mm, δ = %.3f mm\n\n', ...
    delta_hat_target, a_target*1000, h1_target*1000, L1*1000, delta_target*1000);

%% 根据 γ 计算 d
% d = h / γ_target
d_target = h1_target / (gamma_target-1);
% h_target = h1_target + d_target
h_target = h1_target + d_target;

h2_target = h1_target + 2*d_target;

rho_target = (1 - a_hat_target^2) / (gamma_target - 1)^2;
delta_hat1_target = 1 - sqrt(1 + 2*sqrt(1 - a_hat_target^2)*sqrt(rho_target) + rho_target) + delta_hat_target;
delta_hat2_target = 1 - sqrt(1 + 4*sqrt(1 - a_hat_target^2)*sqrt(rho_target) + 4*rho_target) + delta_hat_target;

delta1_target = delta_hat1_target * sqrt(a_target^2 + h1_target^2);
delta2_target = delta_hat2_target * sqrt(a_target^2 + h1_target^2);

L2 = sqrt(a_target^2 + h_target^2) + delta1_target;
L3 = sqrt(a_target^2 + h2_target^2) + delta2_target;

fprintf('根据 â = %.3f, γ = %.3f 计算得到: ρ = %.3f \n\n', ...
    a_hat_target, gamma_target, rho_target);
fprintf('根据 â = %.3f, ρ= %.3f, δ̂= %.3f 计算得到: δ̂_1 = %.3f, δ̂_2 = %.3f, 此时, δ_1 = %.3f mm, δ_2 = %.3f mm, L2 = %.3f mm, L3 = %.3f mm\n\n', ...
    a_hat_target, rho_target,delta_hat_target, delta_hat1_target, delta_hat2_target, delta1_target*1000, delta2_target*1000, L2*1000, L3*1000);

%% 参数范围
k1_range = 1:10:2000;        % 上斜弹簧刚度 N/m

fprintf('=====================================================================================================================================================================================================================================\n');
fprintf(' k₁(N/m) | h_target(mm) | h₁(mm) | h₂ (mm) | d_target(mm) | k₂(N/m) | k₃(N/m) | a_target(mm) | h₁_target(mm) | δ_target(mm) | δ1_target(mm) | δ2_target(mm) | δ3_target(mm) | L₀(mm) | L(mm) \n');
fprintf('-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n');

colors = lines(length(k1_range));
found_count = 0;
y_hat = linspace(-10, 10, 1000);
h_iterated = [];
iter_legend_str = '';

max_len = length(k1_range);
y_hat_fig1 = cell(1, max_len); %figure1对应的y_hat
f_hat      = cell(1, max_len); %figure1对应的f_hat
K_hat_fig1 = cell(1, max_len); %figure1对应的K_hat
k1_record  = zeros(1, max_len); %figure1里面循环迭代的K1的个数
k2_record  = zeros(1, max_len); % 用于存储提取出的 k2 值

for k1 = k1_range
    %% 根据 α 和 α₁ 计算 k2, k3
    % k₂ = k₁ / α_target
    k2 = k1 / alpha_target;
    % k₃ = α₁_target · k₂
    k3 = alpha1_target * k2;

%刚度
k = (G * d^4) / (8 * D^3 * n) ;
%切应力
tau = (8 * F * D) / (pi * d^3) * K;
%曲度系数
K = (4*C - 1) / (4*C - 4) + 0.615 / C;
% 旋绕比
C = D/d;

















    %% 计算实际无量纲参数
    a_hat_actual    = a_target / sqrt(a_target^2 + h1_target^2);
    gamma_actual    = h_target / d_target;
    delta_hat_actual = delta_target / sqrt(a_target^2 + h1_target^2);
    alpha_actual    = k1 / k2;
    alpha1_actual   = k3 / k2;

    %% 计算K2的预压缩量
    f1 = -k1*delta_target*h1_target/sqrt(a_target^2+h1_target^2);
    f3 = -k3*delta1_target*h_target/sqrt(a_target^2+h_target^2);
    f4 = -k1*delta2_target*h2_target/sqrt(a_target^2+h2_target^2);
    f2 = 2*f1 + 2*f3 +2*f4;
    delta3_target = f2/k2;
    L = h2_target + delta3_target;
    % fprintf('delta3_target =%.3f\n,delta_target=%.3f\n,delta1_target=%.3f\n,delta2_target=%.3f\n',delta3_target,delta_target,delta1_target,delta2_target);

    %% 计算误差（由于 a_target, h1_target, delta_target 是精确计算的）
    err_a_hat = abs(a_hat_actual - a_hat_target);
    err_delta = abs(delta_hat_actual - delta_hat_target);
    err_gamma = abs(gamma_actual - gamma_target);
    err_alpha = abs(alpha_actual - alpha_target);
    err_alpha1 = abs(alpha1_actual - alpha1_target);

    tolerance = 1e-5;
    if err_a_hat < tolerance && err_delta < tolerance && ...
            err_gamma < tolerance && err_alpha < tolerance && ...
            err_alpha1 < tolerance

        found_count = found_count + 1;

        fprintf('   %4.0f | %6.2f | %6.2f | %6.2f |     %6.2f   | %7.2f | %7.2f |     %.2f    |      %.2f    |    %6.2f   |     %6.2f    |    %6.2f    |    %6.2f   |  %6.2f  | %6.2f \n', ...
            k1, h_target*1000, h1_target*1000, h2_target*1000,d_target*1000, k2, k3, a_target*1000, h1_target*1000, delta_target*1000,delta1_target*1000,delta2_target*1000,delta3_target*1000, L1*1000,L*1000);

        fprintf('=======================================================输出可能的参数组合======================================================================================================================================\n');

        %% 计算无量纲恢复力曲线（f_hat & xi_hat）
        % 中间变量
        % ρ = (1 - â²) / (γ - 1)²
        rho_actual = (1 - a_hat_actual^2) / (gamma_actual - 1)^2;
        % Δ = √(1 + â²·γ² - 2·â²·γ)
        Delta_actual = sqrt(1 + a_hat_actual^2 * gamma_actual^2 - 2 * a_hat_actual^2 * gamma_actual);
        % Δ₁ = (1 + δ̂)·(γ - 1)
        Delta1_actual = (1 + delta_hat_actual) * (gamma_actual - 1);
        % Δ₂ = (1 + δ̂)·(γ - 1)³
        Delta2_actual = (1 + delta_hat_actual) * (gamma_actual - 1)^3;
        % C₁ = 6·(1 + δ̂)·â⁻³ / [-12·Δ₂/Δ³ + 72·Δ₂·(1 - â²)/Δ⁵ - 60·Δ₂·(1 - â²)²/Δ⁷]
        C1_actual = 6*(1 + delta_hat_actual) * a_hat_actual^(-3) / (-12*Delta2_actual/Delta_actual^3 + 72*Delta2_actual*(1-a_hat_actual^2)/Delta_actual^5 - 60*Delta2_actual*(1-a_hat_actual^2)^2/Delta_actual^7);

        %% 弹簧自由长度相同推导得到的
        % δ̂₁ = 1 - √(1 + 2·√(1 - â²)·√ρ + ρ) + δ̂
        delta_hat1_actual = 1 - sqrt(1 + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho_actual) + rho_actual) + delta_hat_actual;
        %% f1_hat = f4_hat 推导得到的
        % δ̂₂ = 1 - √(1 + 4·√(1 - â²)·√ρ + 4·ρ) + δ̂
        delta_hat2_actual = 1 - sqrt(1 + 4*sqrt(1 - a_hat_actual^2)*sqrt(rho_actual) + 4*rho_actual) + delta_hat_actual;

        %% 位移
        % x̂_e = √(1 − â²) + √ρ
        x_e_hat_actual = sqrt(1 - a_hat_actual^2) + sqrt(rho_actual);
        % K̂ = zeros(size(ŷ))

        %% 创建向量
        K_hat = zeros(size(y_hat));
        xi_hat = zeros(size(y_hat));
        f_hat_curve1 = zeros(size(y_hat)); %figure1对应的f_hat
        y_hat_curve1 = zeros(size(y_hat)); %figure1对应的y_hat

        for i = 1:length(y_hat)
            % x_i = x̂_e + ŷ(i)
            xi_hat(i) = x_e_hat_actual + y_hat(i);
            % P₁ = √(1−â²) − xi_hat(i)
            P1 = sqrt(1 - a_hat_actual^2) - xi_hat(i);
            % P₂ = 1 − 2√(1−â²)·xi_hat + xi_hat(i)²
            P2 = 1 - 2*sqrt(1 - a_hat_actual^2)*xi_hat(i) + xi_hat(i)^2;
            % P₃ = 1 + δ̂
            P3 = 1 + delta_hat_actual;
            % P₄ = √(1−â²+ρ+2√(1−â²)√ρ) − xi_hat(i)
            P4 = sqrt(1 - a_hat_actual^2 + rho_actual + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho_actual)) - xi_hat(i);
            % P₅ = 1+ρ+2√(1−â²)√ρ − 2√(1−â²+ρ+2√(1−â²)√ρ)·xi_hat + xi_hat(i)²
            P5 = 1 + rho_actual + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho_actual) - 2*sqrt(1 - a_hat_actual^2 + rho_actual + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho_actual))*xi_hat(i) + xi_hat(i)^2;
            % P₆ = √(1+2√(1−â²)√ρ+ρ) + δ̂₁
            P6 = sqrt(1 + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho_actual) + rho_actual) + delta_hat1_actual;
            % P₇ = √(1−â²) + 2√ρ − xi_hat(i)
            P7 = sqrt(1 - a_hat_actual^2) + 2*sqrt(rho_actual) - xi_hat(i);
            % P₈ = 1+4√(1−â²)√ρ+4ρ − 2(√(1−â²)+2√ρ)xi_hat + xi_hat(i)²
            P8 = 1 + 4*sqrt(1 - a_hat_actual^2)*sqrt(rho_actual) + 4*rho_actual - 2*(sqrt(1 - a_hat_actual^2) + 2*sqrt(rho_actual))*xi_hat(i) + xi_hat(i)^2;
            % P₉ = √(1+4√(1−â²)√ρ+4ρ) + δ̂₂
            P9 = sqrt(1 + 4*sqrt(1 - a_hat_actual^2)*sqrt(rho_actual) + 4*rho_actual) + delta_hat2_actual;
            % dP₁ = dP₄ = dP₇ = -1
            dP1 = -1; dP4 = -1; dP7 = -1;
            % dP₂ = −2√(1−â²) + 2xi_hat
            dP2 = -2*sqrt(1 - a_hat_actual^2) + 2*xi_hat(i);
            % dP₅ = −2√(1−â²+ρ+2√(1−â²)√ρ) + 2xi_hat
            dP5 = -2*sqrt(1 - a_hat_actual^2 + rho_actual + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho_actual)) + 2*xi_hat(i);
            % dP₈ = −2(√(1−â²)+2√ρ) + 2xi_hat
            dP8 = -2*(sqrt(1 - a_hat_actual^2) + 2*sqrt(rho_actual)) + 2*xi_hat(i);
            % dN₁ = −2α(1−P₃·P₂^{−1/2})·dP₁ − α·P₁·P₂^{−3/2}·P₃·dP₂
            dN1 = -2 * alpha_actual * (1 - P3 * P2.^(-0.5)) * (-1) - alpha_actual * P1 * P2.^(-1.5) * P3 * dP2;
            % dN₃ = −2α₁(1−P₆·P₅^{−1/2})·dP₄ − α₁·P₄·P₅^{−3/2}·P₆·dP₅
            dN3 = -2 * alpha1_actual * (1 - P6 * P5.^(-0.5)) * (-1) - alpha1_actual * P4 * P5.^(-1.5) * P6 * dP5;
            % dN₅ = −2α(1−P₉·P₈^{−1/2})·dP₇ − α·P₇·P₈^{−3/2}·P₉·dP₈
            dN5 = -2 * alpha_actual * (1 - P9 * P8.^(-0.5)) * (-1) - alpha_actual * P7 * P8.^(-1.5) * P9 * dP8;

            %% 无量纲刚度&力 K̂(i) = 1 + dN₁ + dN₃ + dN₅
            K_hat(i) = 1 + dN1 + dN3 + dN5;
            f_hat_curve1(i) = xi_hat(i) - 2*alpha_actual * P1*(sqrt(P2)-P3)/sqrt(P2) - 2*alpha1_actual * P4*(sqrt(P5)-P6)/sqrt(P5) - 2*alpha_actual * P7*(sqrt(P8)-P9)/sqrt(P8);
            y_hat_curve1(i) = xi_hat(i) - x_e_hat_actual;
        end

        %% 循环输出变量到数组
        y_hat_fig1{found_count} = y_hat_curve1;
        f_hat{found_count}      = f_hat_curve1;
        K_hat_fig1{found_count} = K_hat;
        k1_record(found_count)  = k1;
        k2_record(found_count)  = k2;

    end
end

y_hat_fig1(found_count+1:end) = [];
f_hat(found_count+1:end)      = [];
K_hat_fig1(found_count+1:end) = [];
k1_record(found_count+1:end)  = [];
k2_record(found_count+1:end)  = [];

%% 绘制第 n 组无量纲刚度和力的双y轴图
if found_count > 0
    target_idx = 8;
    if target_idx > found_count
        target_idx = found_count;
    end

    figure(1);
    set(gcf, 'Position', [100, 100, 600, 450], 'Visible', 'off');

    yyaxis left
    plot(y_hat_fig1{target_idx}, f_hat{target_idx}, 'Color',[0, 0.4470, 0.7410],'LineWidth', 2);
    ylabel('Dimensionless Force $\hat{f}$', 'Interpreter', 'latex', 'FontSize', 18);
    ylim([-6, 6]); xlim([-3, 3]);

    yyaxis right
    plot(y_hat_fig1{target_idx}, K_hat_fig1{target_idx}, 'Color',[0.8500, 0.3250, 0.0980],'LineStyle','--', 'LineWidth', 2);
    ylabel('Dimensionless Stiffness $\hat{K}$', 'Interpreter', 'latex', 'FontSize', 18);

    title(['Results for Parameter Set No. ', num2str(target_idx)], 'FontSize', 24);
    xlabel('Dimensionless Displacement $\hat{y}$', 'Interpreter', 'latex', 'FontSize', 18);
    set(gca,'FontSize',16);   % 坐标刻度的大小
    grid on; %显示网格

    legend(sprintf('Force'), ...
        sprintf('Stiffness'), ...
        'Interpreter', 'latex', 'Location', 'best','FontSize',14);
else
    disp('未找到有效参数组合');
end
fprintf('可能的参数组合%d\n',found_count);

%% ====================================================Figure1 end=================================================================%%
%% 计算目标参数的总刚度曲线 [delyijita_hat, a_hat, gamma] => 计算得到alpha & alpha1
test_params = [
    0.500, 0.755, 2.143, 0.942, 0.501;
    0.700, 0.875, 1.728, NaN, NaN;
    0.800, 0.800, 1.987, NaN, NaN;
    0.500, 0.800, 1.987, NaN, NaN;
    0.200, 0.800, 2.192, NaN, NaN];

num_test = size(test_params, 1); %test_params有几组参数
base_colors = lines(num_test); %生成num_test组颜色
line_styles = {'-', '--', ':', '-.'};
test_styles = cell(1, num_test);

% 填充线形
for i = 1:num_test
    style_idx = mod(i-1, length(line_styles)) + 1;
    test_styles{i} = line_styles{style_idx};
end

% 填充颜色
test_color_specs = cell(1, num_test);
for i = 1:num_test
    rgb = base_colors(i, :);
    test_color_specs{i} = {rgb, test_styles{i}};
end

%% 初始化存储句柄和图例文本
h_targets = gobjects(1, num_test);  %存储曲线句柄
target_legends = cell(1, num_test);  %存储图例文字

%% alpha和alpha1
num_test = size(test_params, 1);
alpha_store = zeros(num_test, 1);
alpha1_store = zeros(num_test, 1);

fprintf('\n五个无量纲参数计算结果:\n');
fprintf('-------------------------------------------------------------------------------------------\n');
fprintf('  Group  |   delta_hat (δ̂) |   a_hat (â)   |   gamma (γ)   |   alpha (α)   |   alpha1 (α1) \n');
fprintf('-------------------------------------------------------------------------------------------\n');

figure(2);
set(gcf, 'Position', [100, 100, 750, 520], 'Visible', 'on');
set(gca,'FontSize',16);
grid on;
hold on; %不能删，显示后面legend

for j = 1:size(test_params, 1)
    %% 提取test_params中delta_hat, a_hat, gamma
    delta_hat = test_params(j,1);
    a_hat = test_params(j,2);
    gamma = test_params(j,3);

    if size(test_params, 2) >= 5 && ~isnan(test_params(j,4)) && ~isnan(test_params(j,5))
        alpha = test_params(j,4);
        alpha1 = test_params(j,5);
        calculated = false;
        alpha_store(j) = round(alpha, 3);
        alpha1_store(j) = round(alpha1, 3);
    else

        % Δ = √(1 + â²·γ² - 2·â²·γ)
        Delta = sqrt(1 + a_hat^2 * gamma^2 - 2 * a_hat^2 * gamma);
        % Δ₁ = (1 + δ̂)·(γ - 1)
        Delta1 = (1 + delta_hat) * (gamma- 1);
        % Δ₂ = (1 + δ̂)·(γ - 1)³
        Delta2 = (1 + delta_hat) * (gamma - 1)^3;
        % C₁ = 6·(1 + δ̂)·â⁻³ / [-12·Δ₂/Δ³ + 72·Δ₂·(1 - â²)/Δ⁵ - 60·Δ₂·(1 - â²)²/Δ⁷]
        C1 = 6*(1 + delta_hat) * a_hat^(-3) / (-12*Delta2/Delta^3 + 72*Delta2*(1-a_hat^2)/Delta^5 - 60*Delta2*(1-a_hat^2)^2/Delta^7);
        % α₁ = −1 / { C₁·[ 4 − 4·Δ₁/Δ + 4·(1 − â²)·Δ₁/Δ³ ] + 2·[ 1 − (1 + δ)/â ] }
        alpha1 = -1/(C1*(4-4*Delta1/Delta + 4*(1-a_hat^2)*Delta1/Delta^3)+ 2*(1-(1 + delta_hat)/a_hat));
        % α = C₁ · α₁
        alpha = C1 * alpha1;

        %% 存储alpha和alpha1
        %alpha_store(j) = alpha;
        alpha_store(j) = round(alpha, 3);
        %alpha1_store(j) = alpha1;
        alpha1_store(j) = round(alpha1, 3);
    end

    % K̂_target = zeros(size(ŷ))
    K_hat_target = zeros(size(y_hat));
    % ρ = (1 − â²) / (γ − 1)²
    rho = (1 - a_hat^2) / (gamma - 1)^2;
    % δ̂₁ = 1 − √[ 1 + 2·√(1 − â²)·√ρ + ρ ] + δ̂
    delta_hat1 = 1 - sqrt(1 + 2*sqrt(1 - a_hat^2)*sqrt(rho) + rho) + delta_hat;
    % δ̂₂ = 1 − √[ 1 + 4·√(1 − â²)·√ρ + 4·ρ ] + δ̂
    delta_hat2 = 1 - sqrt(1 + 4*sqrt(1 - a_hat^2)*sqrt(rho) + 4*rho) + delta_hat;
    % x ̂_e = √(1 − â²) + √ρ
    x_e_hat = sqrt(1 - a_hat^2) + sqrt(rho);

    for i = 1:length(y_hat)
        % xi_hat(i) = x̂_e + ŷ(i)
        xi_hat(i) = x_e_hat + y_hat(i);
        % P₁ = √(1 − â²) − xi_hat(i)
        P1 = sqrt(1 - a_hat^2) - xi_hat(i);
        % P₂ = 1 − 2·√(1 − â²)·xi_hat + xi_hat(i)²
        P2 = 1 - 2*sqrt(1 - a_hat^2)*xi_hat(i) + xi_hat(i)^2;
        % P₃ = 1 + δ̂
        P3 = 1 + delta_hat;
        % P₄ = √(1 − â² + ρ + 2·√(1 − â²)·√ρ) − xi_hat(i)
        P4 = sqrt(1 - a_hat^2 + rho + 2*sqrt(1 - a_hat^2)*sqrt(rho)) - xi_hat(i);
        % P₅ = 1 + ρ + 2·√(1 − â²)·√ρ − 2·√(1 − â² + ρ + 2·√(1 − â²)·√ρ)·xi_hat + xi_hat(i)²
        P5 = 1 + rho + 2*sqrt(1 - a_hat^2)*sqrt(rho) - 2*sqrt(1 - a_hat^2 + rho + 2*sqrt(1 - a_hat^2)*sqrt(rho))*xi_hat(i) + xi_hat(i)^2;
        % P₆ = √(1 + 2·√(1 − â²)·√ρ + ρ) + δ̂₁
        P6 = sqrt(1 + 2*sqrt(1 - a_hat^2)*sqrt(rho) + rho) + delta_hat1;
        % P₇ = √(1 − â²) + 2·√ρ − xi_hat(i)
        P7 = sqrt(1 - a_hat^2) + 2*sqrt(rho) - xi_hat(i);
        % P₈ = 1 + 4·√(1 − â²)·√ρ + 4·ρ − 2·(√(1 − â²) + 2·√ρ)·xi_hat + xi_hat(i)²
        P8 = 1 + 4*sqrt(1 - a_hat^2)*sqrt(rho) + 4*rho - 2*(sqrt(1 - a_hat^2) + 2*sqrt(rho))*xi_hat(i) + xi_hat(i)^2;
        % P₉ = √(1 + 4·√(1 − â²)·√ρ + 4·ρ) + δ̂₂
        P9 = sqrt(1 + 4*sqrt(1 - a_hat^2)*sqrt(rho) + 4*rho) + delta_hat2;
        % dP₂ = −2·√(1 − â²) + 2·xi_hat
        dP2 = -2*sqrt(1 - a_hat^2) + 2*xi_hat(i);
        % dP₅ = −2·√(1 − â² + ρ + 2·√(1 − â²)·√ρ) + 2·xi_hat
        dP5 = -2*sqrt(1 - a_hat^2 + rho + 2*sqrt(1 - a_hat^2)*sqrt(rho)) + 2*xi_hat(i);
        % dP₈ = −2·(√(1 − â²) + 2·√ρ) + 2·xi_hat
        dP8 = -2*(sqrt(1 - a_hat^2) + 2*sqrt(rho)) + 2*xi_hat(i);
        % dN₁ = −2·α·(1 − P₃·P₂⁻⁰·⁵)·(−1) − α·P₁·P₂⁻¹·⁵·P₃·dP₂
        dN1 = -2 * alpha * (1 - P3 * P2.^(-0.5)) * (-1) - alpha * P1 * P2.^(-1.5) * P3 .* dP2;
        % dN₃ = −2·α₁·(1 − P₆·P₅⁻⁰·⁵)·(−1) − α₁·P₄·P₅⁻¹·⁵·P₆·dP₅
        dN3 = -2 * alpha1 * (1 - P6 * P5.^(-0.5)) * (-1) - alpha1 * P4 * P5.^(-1.5) * P6 .* dP5;
        % dN₅ = −2·α·(1 − P₉·P₈⁻⁰·⁵)·(−1) − α·P₇·P₈⁻¹·⁵·P₉·dP₈
        dN5 = -2 * alpha * (1 - P9 * P8.^(-0.5)) * (-1) - alpha * P7 * P8.^(-1.5) * P9 .* dP8;
        % K̂_hat(i) = 1 + dN₁ + dN₃ + dN₅
        K_hat(i) = 1 + dN1 + dN3 + dN5;

    end

    %% 输出五个无量纲参数
    fprintf('    %d    |      %.3f      |     %.3f     |     %.3f     |     %.4f     |     %.4f\n', ...
        j, delta_hat, a_hat, gamma, alpha, alpha1);

    %% for图例
    h_targets(j) = plot(y_hat, K_hat, 'Color', test_color_specs{j}{1}, ...
        'LineStyle', test_color_specs{j}{2}, 'LineWidth', 3);
    target_legends{j} = sprintf('$\\hat{a}=%.3f, \\hat{\\delta}=%.3f, \\gamma=%.3f, \\alpha=%.3f, \\alpha_1=%.3f$', ...
        a_hat, delta_hat, gamma, alpha, alpha1);
end

% 图例
legend(h_targets, target_legends, ...
    'Interpreter', 'latex', 'Location', 'best', 'FontSize', 12);

xline(0, '--', 'Color', [0.5, 0.5, 0.5], 'LineWidth', 1.5,'HandleVisibility', 'off');
xlabel('$\hat{y}$', 'Interpreter', 'latex', 'FontSize', 18);
ylabel('$\hat{K}$', 'Interpreter', 'latex', 'FontSize', 18);
xticks([-0.8, -0.5, -0.3, 0, 0.3, 0.5, 0.8]);
title('\textbf{Stiffness curves comparison of QZS}', 'FontSize', 24, 'Interpreter', 'latex');
xlim([-0.8, 0.8]); ylim([-0, 1.5]);

%% ====================================================Figure2 无量纲刚度vs相对于平衡位置的位移图 end=================================================================%%

%% 全参数组泰勒展开计算
fprintf('\nf_hat泰勒展开结果:\n');
num_configs = size(test_params, 1);

mu1_store = zeros(num_configs, 1);
mu3_store = zeros(num_configs, 1);

for j = 1:num_configs
    delta_hat_t = test_params(j, 1);      % δ̂
    a_hat_t = test_params(j, 2);          % â
    gamma_t = test_params(j, 3);          % γ
    alpha_t = alpha_store(j);             % α
    alpha1_t = alpha1_store(j);           % α₁

    % 中间几何变量计算
    rho_t = (1 - a_hat_t^2) / (gamma_t - 1)^2;
    xe_t = sqrt(1 - a_hat_t^2) + sqrt(rho_t);

    %% 计算系数（可以补充推导说明）
    mu0 = sqrt(1-a_hat_t^2) + sqrt(rho_t);
    mu1 = 1 + 4*alpha_t + 2*alpha1_t - 2 * (1 + delta_hat_t) * (2*alpha_t * a_hat_t^2 / (sqrt(rho_t + a_hat_t^2))^3 + alpha1_t/a_hat_t);
    mu3 = (- 2 * (1 + delta_hat_t) * (2*alpha_t*(12*a_hat_t^2*rho_t-3*a_hat_t^4)/((sqrt(rho_t+a_hat_t^2))^7) + alpha1_t*(-3)/a_hat_t^3))/6;

    %% mu1 & mu3 存储到数组
    mu1_store(j) = mu1;
    mu3_store(j) = mu3;

    % 打印输出
    fprintf('Group%d: [δ̂=%.3f, â=%.3f, γ=%.3f, α=%.3f, α₁=%.3f]\n', ...
        j, delta_hat_t, a_hat_t, gamma_t, alpha_t, alpha1_t);
    fprintf('  -> 展开式: f_hat = %.10f*y^3 + %.10f*y + %.3f\n\n', mu3, mu1, mu0);
end

%% ====================================================无量纲力的泰勒展开 end=================================================================%%

%% 位移传递率曲线计算
M = 3;              % kg
g = 9.81;           % m/s^2
mu3_target = 0.0017;

%% 阻尼系数
c = 20;

%% 激励幅值
Ze_mm = 3;
Ze_hat = Ze_mm / 1000 / sqrt(a_target^2 + h1_target^2);  % 无量纲激励幅值

n_max = length(k2_record);
k2_satisfied = zeros(1, n_max);
count = 0;

%% 判断隔振效果
for i = 1:length(k2_record)
    k2 = k2_record(i);

    omega_0 = sqrt(k2/M);
    f0 = omega_0/(2*pi);
    zeta = c * omega_0 / (2 * k2);
    values = Ze_mm * mu3_target * Ze_hat^2/(16 * zeta^2);

    if values <= 1
        count = count + 1;
        k2_satisfied(count) = k2;
    end
end

k2_satisfied = k2_satisfied(1:count);

%% --- 输出结果 ---
fprintf('\n===================隔振效果========================\n');
if isempty(k2_satisfied)
    fprintf('隔振较差的所有 k2 值为：\n');
else
    disp('在提取的 k2 中，均满足3𝜇3𝑍̂𝑒^2∕16𝜁^2 ≥ 1，隔振效果较好。')
    % disp(k2_satisfied');
    fprintf('共计: %d 个\n', length(k2_satisfied));
end

%% 提取 mu1 和 mu3
% 提取 mu1 和 mu3（从泰勒展开结果）
mu1_group1 = 0.1907; %mu1_store(1)
mu3_group1 = 1.3836; %mu3_store(1)
mu1_group2 = 0.1188;
mu3_group2 = 1.2344;
mu1_group3 = 0.000476;
mu3_group3 = 0.001705;
mu1_group4 = 0.3367;
mu3_group4 = 0.3876;
mu1_group5 = 0.2189;
mu3_group5 = 0.2104;

delta_hat_group1 = test_params(1, 1);
a_hat_group1     = test_params(1, 2);
gamma_group1     = test_params(1, 3);
alpha_group1     = alpha_store(1);
alpha1_group1    = alpha1_store(1);

delta_hat_group2 = test_params(2, 1);
a_hat_group2     = test_params(2, 2);
gamma_group2     = test_params(2, 3);
alpha_group2     = alpha_store(2);
alpha1_group2    = alpha1_store(2);

delta_hat_group3 = test_params(3, 1);
a_hat_group3     = test_params(3, 2);
gamma_group3     = test_params(3, 3);
alpha_group3     = alpha_store(3);
alpha1_group3    = alpha1_store(3);

delta_hat_group4 = test_params(4, 1);
a_hat_group4     = test_params(4, 2);
gamma_group4     = test_params(4, 3);
alpha_group4     = alpha_store(4);
alpha1_group4    = alpha1_store(4);

delta_hat_group5 = test_params(5, 1);
a_hat_group5     = test_params(5, 2);
gamma_group5     = test_params(5, 3);
alpha_group5     = alpha_store(5);
alpha1_group5    = alpha1_store(5);

%% 频率扫描 for绘图 (Figure 3 & 4)
f_ex = linspace(0.1, 10, 1000);
Ta_group1 = zeros(size(f_ex));
Ta_group2 = zeros(size(f_ex));
Ta_group3 = zeros(size(f_ex));
Ta_group4 = zeros(size(f_ex));
Ta_group5 = zeros(size(f_ex));

for j = 1:length(f_ex)
    Omega = f_ex(j) / f0;
    Ta_group1(j) = compute_transmissibility(mu1_group1, mu3_group1, Omega, Ze_hat, zeta);
    Ta_group2(j) = compute_transmissibility(mu1_group2, mu3_group2, Omega, Ze_hat, zeta);
    Ta_group3(j) = compute_transmissibility(mu1_group3, mu3_group3, Omega, Ze_hat, zeta);
    Ta_group4(j) = compute_transmissibility(mu1_group4, mu3_group4, Omega, Ze_hat, zeta);
    Ta_group5(j) = compute_transmissibility(mu1_group5, mu3_group5, Omega, Ze_hat, zeta);
end

%% 生成图例字符串
params_group1 = sprintf('$\\hat{\\delta}=%.3f,\\ \\hat{a}=%.3f,\\ \\gamma=%.3f,\\ \\alpha=%.3f,\\ \\alpha_1=%.3f$', ...
    delta_hat_group1, a_hat_group1, gamma_group1, alpha_group1, alpha1_group1);
params_group2 = sprintf('$\\hat{\\delta}=%.3f,\\ \\hat{a}=%.3f,\\ \\gamma=%.3f,\\ \\alpha=%.3f,\\ \\alpha_1=%.3f$', ...
    delta_hat_group2, a_hat_group2, gamma_group2, alpha_group2, alpha1_group2);
params_group3 = sprintf('$\\hat{\\delta}=%.3f,\\ \\hat{a}=%.3f,\\ \\gamma=%.3f,\\ \\alpha=%.3f,\\ \\alpha_1=%.3f$', ...
    delta_hat_group3, a_hat_group3, gamma_group3, alpha_group3, alpha1_group3);
params_group4 = sprintf('$\\hat{\\delta}=%.3f,\\ \\hat{a}=%.3f,\\ \\gamma=%.3f,\\ \\alpha=%.3f,\\ \\alpha_1=%.3f$', ...
    delta_hat_group4, a_hat_group4, gamma_group4, alpha_group4, alpha1_group4);
params_group5 = sprintf('$\\hat{\\delta}=%.3f,\\ \\hat{a}=%.3f,\\ \\gamma=%.3f,\\ \\alpha=%.3f,\\ \\alpha_1=%.3f$', ...
    delta_hat_group5, a_hat_group5, gamma_group5, alpha_group5, alpha1_group5);

%% 传递率图: 显示五个无量纲参数
figure(3);
set(gcf, 'Position', [100, 100, 950, 650], 'Visible', 'on');
set(gca, 'FontSize', 16, 'FontName', 'Times New Roman');
hold on;
grid on;

h1 = plot(f_ex, Ta_group1, 'b--', 'LineWidth', 1.5); hold on;
h2 = plot(f_ex, Ta_group2, 'r-', 'LineWidth', 1.5);
h3 = plot(f_ex, Ta_group3, 'g-.', 'LineWidth', 1.5);
h4 = plot(f_ex, Ta_group4, 'm:', 'LineWidth', 1.5);
h5 = plot(f_ex, Ta_group5, 'c-', 'LineWidth', 1.5);

yline(1, '--', 'Color', [0.5, 0.5, 0.5], 'LineWidth', 1.5,'HandleVisibility', 'off');

xlabel('Frequency (Hz)', 'FontSize', 22);
ylabel('Transmissibility $T_a$', 'Interpreter', 'latex', 'FontSize', 22, 'FontWeight', 'bold');
title(['\textbf{Displacement Transmissibility ($\zeta = $', num2str(zeta), ', $Z_e = $', num2str(Ze_mm), 'mm)}'], ...
    'Interpreter', 'latex', 'FontSize', 24);

xlim([0, 10]); ylim([0, 10]);
set(gca, 'XTick', 0:2:10, 'YTick', 0:2:12);

legend([h1, h2, h3, h4, h5], ...
    {params_group1, params_group2, params_group3, params_group4, params_group5}, ...
    'Location', 'northeast', 'FontSize', 13, 'Interpreter', 'latex');

%% 图1的小窗口
axes('Position', [0.60, 0.40, 0.25, 0.25]);
f_inset = linspace(6, 10, 200);
Omega_inset = f_inset / f0;

Ta_group1_inset = zeros(size(f_inset));
Ta_group2_inset = zeros(size(f_inset));
Ta_group3_inset = zeros(size(f_inset));
Ta_group4_inset = zeros(size(f_inset));
Ta_group5_inset = zeros(size(f_inset));

for i = 1:length(f_inset)
    Omega = Omega_inset(i);
    Ta_group1_inset(i) = compute_transmissibility(mu1_group1,  mu3_group1, Omega, Ze_hat, zeta);
    Ta_group2_inset(i) = compute_transmissibility(mu1_group2,  mu3_group2, Omega, Ze_hat, zeta);
    Ta_group3_inset(i) = compute_transmissibility(mu1_group3,  mu3_group3, Omega, Ze_hat, zeta);
    Ta_group4_inset(i) = compute_transmissibility(mu1_group4,  mu3_group4, Omega, Ze_hat, zeta);
    Ta_group5_inset(i) = compute_transmissibility(mu1_group5,  mu3_group5, Omega, Ze_hat, zeta);
end

plot(f_inset, Ta_group1_inset, 'b--', 'LineWidth', 1.2); hold on;
plot(f_inset, Ta_group2_inset, 'r-', 'LineWidth', 1.2);
plot(f_inset, Ta_group3_inset, 'g-.', 'LineWidth', 1.2);
plot(f_inset, Ta_group4_inset, 'm:', 'LineWidth', 1.2);
plot(f_inset, Ta_group5_inset, 'c-', 'LineWidth', 1.2);

xlim([6, 10]); ylim([0, 0.25]);
set(gca, 'FontSize', 12, 'FontName', 'Times New Roman');
xlabel('Frequency (Hz)', 'FontSize', 16);
ylabel('$T_a$', 'Interpreter', 'latex', 'FontSize', 16);

%% 传递率图2: 显示 μ₁和μ₃ 取值
figure(4);
set(gcf, 'Position', [100, 100, 950, 650]);
set(gca, 'FontSize', 16, 'FontName', 'Times New Roman', 'Visible', 'on');
hold on;
grid on;

plot(f_ex, Ta_group1, 'b--', 'LineWidth', 1.5); hold on;
plot(f_ex, Ta_group2, 'r-', 'LineWidth', 1.5);
plot(f_ex, Ta_group3, 'g-.', 'LineWidth', 1.5);
plot(f_ex, Ta_group4, 'm:', 'LineWidth', 1.5);
plot(f_ex, Ta_group5, 'c-', 'LineWidth', 1.5);

yline(1, '--', 'Color', [0.5, 0.5, 0.5], 'LineWidth', 1.5,'HandleVisibility', 'off');

set(gca, 'FontSize', 14, 'FontName', 'Times New Roman');
xlabel('Frequency (Hz)', 'FontSize', 22);
ylabel('Transmissibility $T_a$', 'Interpreter', 'latex', 'FontSize', 22, 'FontWeight', 'bold');
title(['\textbf{Displacement Transmissibility ($\zeta = $', num2str(zeta), ', $Z_e = $', num2str(Ze_mm), 'mm)}'], ...
    'Interpreter', 'latex', 'FontSize', 24);

xlim([0, 10]); ylim([0, 10]);
set(gca, 'XTick', 0:2:10, 'YTick', 0:2:12);

legend({sprintf('$\\mu_1=%.5f,\\ \\mu_3=%.5f$', mu1_group1, mu3_group1), ...
    sprintf('$\\mu_1=%.5f,\\ \\mu_3=%.5f$', mu1_group2, mu3_group2), ...
    sprintf('$\\mu_1=%.5f,\\ \\mu_3=%.5f$', mu1_group3, mu3_group3), ...
    sprintf('$\\mu_1=%.5f,\\ \\mu_3=%.5f$', mu1_group4, mu3_group4), ...
    sprintf('$\\mu_1=%.5f,\\ \\mu_3=%.5f$', mu1_group5, mu3_group5)}, ...
    'Location', 'northeast', 'FontSize', 15, 'Interpreter', 'latex');

%% 图2的小窗
axes('Position', [0.60, 0.40, 0.25, 0.25]);

plot(f_inset, Ta_group1_inset, 'b--', 'LineWidth', 1.2); hold on;
plot(f_inset, Ta_group2_inset, 'r-', 'LineWidth', 1.2);
plot(f_inset, Ta_group3_inset, 'g-.', 'LineWidth', 1.2);
plot(f_inset, Ta_group4_inset, 'm:', 'LineWidth', 1.2);
plot(f_inset, Ta_group5_inset, 'c-', 'LineWidth', 1.2);

xlim([6, 10]); ylim([0, 0.25]);
set(gca, 'FontSize', 12, 'FontName', 'Times New Roman');
xlabel('Frequency (Hz)', 'FontSize', 16);
ylabel('$T_a$', 'Interpreter', 'latex', 'FontSize', 16);

%% 输出结果
fprintf('\n========== 传递率计算用到的参数 ==========\n');
fprintf('参考频率 f0 = %.3f Hz\n', f0);
fprintf('激励幅值 Z_e = %.3f mm (无量纲: %.4f)\n', Ze_mm, Ze_hat);
fprintf('阻尼比 ζ = %.3f\n\n', zeta);

%% 读取CSV文件并计算传递后响应
[filename, filepath] = uigetfile('*.csv', '请选择包含振动数据的CSV文件');
if isequal(filename, 0), return; end

fullpath = fullfile(filepath, filename);
data = readmatrix(fullpath, 'NumHeaderLines', 3);
t = data(:, 1);
v_in = (data(:, 2) / 100);
v_in = v_in - mean(v_in);
dt = t(2) - t(1);
fs = 1 / dt;
N = length(v_in);
freq = (0:N-1) * fs / N;
n_pos = floor(N/2);
freq_range = freq(1:n_pos);
Omega_range = freq_range / f0;

v_out_all = zeros(N, 5);
Ta_curve_all = zeros(5, n_pos);

mu1_vals = [mu1_group1, mu1_group2, mu1_group3, mu1_group4, mu1_group5];
mu3_vals = [mu3_group1, mu3_group2, mu3_group3, mu3_group4, mu3_group5];

for i = 1:5
    mu1 = mu1_vals(i);
    mu3 = mu3_vals(i);
    last_Z = 1.0;
    fprintf('Group%d: mu1=%.4f, mu3=%.4f, f0=%.2f\n', i, mu1, mu3, f0);

    for j = 1:n_pos
        Omega = Omega_range(j);
        Ta_curve_all(i, j) = compute_transmissibility(mu1, mu3, Omega, Ze_hat, zeta);
    end

    H_full = zeros(N, 1);
    H_full(1:n_pos) = Ta_curve_all(i, :);
    H_full(N:-1:N-n_pos+2) = conj(Ta_curve_all(i, 2:n_pos));

    V_in_fft = fft(v_in);
    v_out_all(:, i) = real(ifft(V_in_fft(:) .* H_full));
end

%% 绘制输入输出对比图-时域
colors_map = {[0 0.4470 0.7410], [0.8500 0.3250 0.0980], [0.4660 0.6740 0.1880], [0.4940 0.1840 0.5560], [0.3010 0.7450 0.9330]};

param_names_legend = { ...
    sprintf('Group1: $\\hat{\\delta}=%.3f, \\hat{a}=%.3f, \\gamma=%.3f$', delta_hat_group1, a_hat_group1, gamma_group1), ...
    sprintf('Group2: $\\hat{\\delta}=%.3f, \\hat{a}=%.3f, \\gamma=%.3f$', delta_hat_group2, a_hat_group2, gamma_group2), ...
    sprintf('Group3: $\\hat{\\delta}=%.3f, \\hat{a}=%.3f, \\gamma=%.3f, \\alpha=%.3f, \\alpha_1=%.3f$', delta_hat_group3, a_hat_group3, gamma_group3, alpha_group3, alpha1_group3), ...
    sprintf('Group4: $\\hat{\\delta}=%.3f, \\hat{a}=%.3f, \\gamma=%.3f$', delta_hat_group4, a_hat_group4, gamma_group4), ...
    sprintf('Group5: $\\hat{\\delta}=%.3f, \\hat{a}=%.3f, \\gamma=%.3f$', delta_hat_group5, a_hat_group5, gamma_group5)};

time_show = min(2, t(end));
idx_show = t <= time_show;

figure(5);clf;
set(gcf, 'Position', [100, 100, 950, 650],'Visible', 'on');

subplot(3, 2, 1);
plot(t(idx_show), v_in(idx_show), '--', 'Color', [0.5, 0.5, 0.5], 'LineWidth', 2);
xlabel('Time (s)', 'Interpreter', 'latex', 'FontSize', 22);
ylabel('Voltage (V)', 'Interpreter', 'latex', 'FontSize', 22);
title('Input Signal', 'FontSize', 18, 'Interpreter', 'latex');
set(gca, 'FontSize', 12);
xlim([0, time_show]);
set(gca, 'FontSize', 16, 'FontName', 'Times New Roman');
hold on;
grid on;

for i = 1:5
    subplot(3, 2, i+1);
    plot(t(idx_show), v_out_all(idx_show, i), 'Color', colors_map{i}, 'LineWidth', 1.5);
    xlabel('Time (s)', 'Interpreter', 'latex', 'FontSize', 22);
    ylabel('Voltage (V)', 'Interpreter', 'latex', 'FontSize', 22);
    title(sprintf('Output %d', i), 'FontSize', 18, 'Interpreter', 'latex');
    set(gca, 'FontSize', 12); grid on; box on; xlim([0, time_show]);
end

sgtitle('Voltage Response (Time Domain)', 'FontSize', 28, 'FontWeight', 'bold');

figure(6);clf;
set(gcf, 'Position', [100, 100, 950, 650], 'Visible', 'on');
set(gca, 'FontSize', 16, 'FontName', 'Times New Roman');

window_size = min(length(v_in), 1 * fs);
nfft = 2^nextpow2(window_size);
overlap = nfft/2;
f_psd = (0:nfft/2-1)*fs/nfft;
window = hann(window_size);
window = window ./ sqrt(mean(window.^2));

v_in_psd = compute_psd(v_in, window_size, overlap, nfft, fs, window);
h_in = loglog(f_psd, sqrt(v_in_psd), '--', 'Color', [0.5, 0.5, 0.5], 'LineWidth', 2.5, 'DisplayName', 'Input Signal');
hold on;

h_outs = zeros(1, 5);
for i = 1:5
    v_out_psd = compute_psd(v_out_all(:, i), window_size, overlap, nfft, fs, window);
    h_outs(i) = loglog(f_psd, sqrt(v_out_psd), 'Color', colors_map{i}, 'LineWidth', 2, ...
        'DisplayName', param_names_legend{i});
end

set(gca, 'FontSize', 16);
xlabel('Frequency (Hz)', 'Interpreter', 'latex', 'FontSize', 22);
ylabel('PSD $[V/\sqrt{Hz}]$', 'Interpreter', 'latex', 'FontSize', 22);
title('\textbf{Power Spectrum Density Comparison}', 'FontSize', 26, 'Interpreter', 'latex');

lgd = legend([h_in, h_outs], [{'Input Signal'}, param_names_legend], ...
    'Interpreter', 'latex', 'Location', 'northeast', 'FontSize', 13);
set(lgd, 'Position', [0.32, 0.22, 0.2, 0.1]);
xlim([0.5, fs/2]);

%% 传递率计算函数
function Ta = compute_transmissibility(mu1, mu3, Omega, Ze_hat, zeta)
if Omega < 1e-6
    Ta = 1;
    return;
end
%% 30式
a = (9/16) * mu3^2 * Ze_hat^4;
b = 1.5 * mu3 * (mu1 - Omega^2) * Ze_hat^2;
c = (mu1 - Omega^2)^2 + (2*zeta*Omega)^2;
d = -Omega^4;

coeff = [a, b, c, d];
roots_Z2 = roots(coeff);

Z2_candidates = roots_Z2(abs(imag(roots_Z2)) < 1e-6 & real(roots_Z2) > 0);

if isempty(Z2_candidates)
    Z_linear = Omega^2 / sqrt((mu1 - Omega^2)^2 + (2*zeta*Omega)^2);
    Z2 = Z_linear^2;
else
    Z2 = min(real(Z2_candidates));
end

Z_hat = sqrt(Z2);

%% 28式
cos_phi = (0.75 * mu3 * Ze_hat^2 * Z_hat^3 + (mu1 - Omega^2) * Z_hat) / Omega^2;
cos_phi = max(-1, min(1, cos_phi));
Ta = sqrt(1 + 2 * Z_hat * cos_phi + Z_hat^2);
end

function psd = compute_psd(signal, window_size, overlap, nfft, fs, window)
signal = signal(:);
data_frames = buffer(signal, window_size, overlap, 'nodelay');

if size(data_frames, 1) < window_size
    data_frames = data_frames(:, 1:end-1);
end

data_windowed = data_frames .* window;
fft_data = fft(data_windowed, nfft);
psd_matrix = (abs(fft_data(1:nfft/2, :)).^2) / (fs * nfft);

psd_matrix(2:end-1, :) = 2 * psd_matrix(2:end-1, :);
psd = mean(psd_matrix, 2);
end

%% ====================================================传递率图像（使用原文公式进行计算并展开） end=================================================================%%