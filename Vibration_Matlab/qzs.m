clear; clc;

%% 目标无量纲参数
delta_hat_target = 0.5;      % δ̂ = δ / sqrt(a^2 + h1^2) -> (δ)
a_hat_target     = 0.755;    % â = a / sqrt(a^2 + h1^2) ->（h1）
alpha_target     = 0.942;    % α = k1/k2
alpha1_target    = 0.501;    % α₁ = k3/k2
gamma_target     = 2.143;    % γ = h/d

fprintf('目标无量纲参数:\n');
fprintf('  δ̂ = %.3f, â = %.3f, α = %.3f, α₁ = %.3f, γ = %.3f\n\n', ...
    delta_hat_target, a_hat_target, alpha_target, alpha1_target, gamma_target);

%% 铜屏蔽内径 12cm
a = 0.06;     %m

%% 根据 â = a / sqrt(a^2 + h1^2) 反求 h1
% â^2 = a^2 / (a^2 + h1^2)
% a^2 + h1^2 = a^2 / â^2
% h1^2 = a^2/â^2 - a^2 = a^2*(1/â^2 - 1)
h1 = sqrt(a^2 * (1/a_hat_target^2 - 1));

fprintf('根据 â = %.3f 和 a = %.1f mm 计算得到: h1 = %.1f mm\n\n', ...
    a_hat_target, a*1000, h1*1000);

%% 根据 δ̂ = δ / sqrt(a^2 + h1^2) 求 δ
% δ = δ̂ * sqrt(a^2 + h1^2)
delta = delta_hat_target * sqrt(a^2 + h1^2);
L0 = sqrt(a^2 + h1^2) + delta;   % 斜弹簧原始长度（三根弹簧原长相同）

fprintf('根据 δ̂ = %.3f, a = %.1f mm, h1 = %.1f mm 计算得到: L0 = sqrt(a^2+h1^2) + delta = %.1f mm, δ  = δ̂ * sqrt(a^2 + h1^2) = %.3f mm\n\n', ...
    delta_hat_target, a*1000, h1*1000, L0*1000, delta*1000);

%% 参数范围
k1_range = 1:100:2000;        % 上斜弹簧刚度 N/m

y_hat_all = {};
f_hat_all = {};
K_hat_all = {};
k1_record = [];

fprintf('============================================================================================================================================\n');
fprintf(' k₁(N/m) | h(mm) | h₁(mm) | d(mm) | k₂(N/m) | k₃(N/m) | â_act | γ_act | α_act | α₁_act | δ̂_act | a(mm) | h₁(mm) | δ(mm) | L₀(mm) | d(mm)\n');
fprintf('--------------------------------------------------------------------------------------------------------------------------------------------\n');

colors = lines(length(k1_range));
found_count = 0;
y_hat = linspace(-10, 10, 1000);
h_iterated = [];
iter_legend_str = '';

for k1 = k1_range
    %% 根据 γ 计算 d
    % h = h1 + d
    % d = h / γ_target
    d = h1 / (gamma_target-1);
    h = h1 + d;

    %% 根据 α 和 α₁ 计算 k2, k3
    % k₂ = k₁ / α_target
    k2 = k1 / alpha_target;
    % k₃ = α₁_target · k₂
    k3 = alpha1_target * k2;

    % 计算实际无量纲参数
    a_hat_actual    = a / sqrt(a^2 + h1^2);
    gamma_actual    = h / d;
    delta_hat_actual = delta / sqrt(a^2 + h1^2);
    alpha_actual    = k1 / k2;
    alpha1_actual   = k3 / k2;

    % 计算误差（由于 a, h1, delta 是精确计算的）
    err_a_hat = abs(a_hat_actual - a_hat_target);
    err_delta = abs(delta_hat_actual - delta_hat_target);
    err_gamma = abs(gamma_actual - gamma_target);
    err_alpha = abs(alpha_actual - alpha_target);
    err_alpha1 = abs(alpha1_actual - alpha1_target);

    tolerance = 1e-1;
    if err_a_hat < tolerance && err_delta < tolerance && ...
            err_gamma < tolerance && err_alpha < tolerance && ...
            err_alpha1 < tolerance

        found_count = found_count + 1;

        fprintf('%4.0f |%6.2f |%6.2f |%6.2f |%7.2f |%7.2f |%6.2f |%7.4f | %.3f | %.3f | %.3f | %.3f | %.3f | %6.1f | %6.1f | %7.3f | %6.1f | %6.2f\n', ...
            k1, h*1000, h1*1000, d*1000, k2, k3, a*1000, delta*1000, ...
            a_hat_actual, gamma_actual, alpha_actual, alpha1_actual, delta_hat_actual, ...
            a*1000, h1*1000, delta*1000, L0*1000, d*1000);

        %% 计算无量纲恢复力曲线
        %% 中间参数
        % ρ = (1 - â²) / (γ - 1)²
        rho = (1 - a_hat_actual^2) / (gamma_actual - 1)^2;
        % Δ = √(1 + â²·γ² - 2·â²·γ)
        Delta = sqrt(1 + a_hat_actual^2 * gamma_actual^2 - 2 * a_hat_actual^2 * gamma_actual);
        % Δ₁ = (1 + δ̂)·(γ - 1)
        Delta1 = (1 + delta_hat_actual) * (gamma_actual - 1);
        % Δ₂ = (1 + δ̂)·(γ - 1)³
        Delta2 = (1 + delta_hat_actual) * (gamma_actual - 1)^3;
        % C₁ = 6·(1 + δ̂)·â⁻³ / [-12·Δ₂/Δ³ + 72·Δ₂·(1 - â²)/Δ⁵ - 60·Δ₂·(1 - â²)²/Δ⁷]
        C1 = 6*(1 + delta_hat_actual) * a_hat_actual^(-3) / (-12*Delta2/Delta^3 + 72*Delta2*(1-a_hat_actual^2)/Delta^5 - 60*Delta2*(1-a_hat_actual^2)^2/Delta^7);

        %% 自由长度相同推导得到的
        % δ̂₁ = 1 - √(1 + 2·√(1 - â²)·√ρ + ρ) + δ̂
        delta_hat1 = 1 - sqrt(1 + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho) + rho) + delta_hat_actual;
        %% f1_hat = f2_hat 推导得到的
        % δ̂₂ = 1 - √(1 + 4·√(1 - â²)·√ρ + 4·ρ) + δ̂
        delta_hat2 = 1 - sqrt(1 + 4*sqrt(1 - a_hat_actual^2)*sqrt(rho) + 4*rho) + delta_hat_actual;
        % x̂_e = √(1 − â²) + √ρ
        x_e_hat = sqrt(1 - a_hat_actual^2) + sqrt(rho);
        % K̂ = zeros(size(ŷ))
        K_hat = zeros(size(y_hat));

        xi_hat = zeros(size(y_hat));
        f_hat_curve = zeros(size(y_hat));  % 改名
        y_hat_curve = zeros(size(y_hat));

        for i = 1:length(y_hat)
            % x_i = x̂_e + ŷ(i) 
            xi_hat(i) = x_e_hat + y_hat(i);
            % P₁ = √(1−â²) − xi_hat(i)
            P1 = sqrt(1 - a_hat_actual^2) - xi_hat(i);
            % P₂ = 1 − 2√(1−â²)·xi_hat + xi_hat(i)²
            P2 = 1 - 2*sqrt(1 - a_hat_actual^2)*xi_hat(i) + xi_hat(i)^2;
            % P₃ = 1 + δ̂
            P3 = 1 + delta_hat_actual;
            % P₄ = √(1−â²+ρ+2√(1−â²)√ρ) − xi_hat(i)
            P4 = sqrt(1 - a_hat_actual^2 + rho + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho)) - xi_hat(i);
            % P₅ = 1+ρ+2√(1−â²)√ρ − 2√(1−â²+ρ+2√(1−â²)√ρ)·xi_hat + xi_hat(i)²
            P5 = 1 + rho + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho) - 2*sqrt(1 - a_hat_actual^2 + rho + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho))*xi_hat(i) + xi_hat(i)^2;
            % P₆ = √(1+2√(1−â²)√ρ+ρ) + δ̂₁
            P6 = sqrt(1 + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho) + rho) + delta_hat1;
            % P₇ = √(1−â²) + 2√ρ − xi_hat(i)
            P7 = sqrt(1 - a_hat_actual^2) + 2*sqrt(rho) - xi_hat(i);
            % P₈ = 1+4√(1−â²)√ρ+4ρ − 2(√(1−â²)+2√ρ)xi_hat + xi_hat(i)²
            P8 = 1 + 4*sqrt(1 - a_hat_actual^2)*sqrt(rho) + 4*rho - 2*(sqrt(1 - a_hat_actual^2) + 2*sqrt(rho))*xi_hat(i) + xi_hat(i)^2;
            % P₉ = √(1+4√(1−â²)√ρ+4ρ) + δ̂₂
            P9 = sqrt(1 + 4*sqrt(1 - a_hat_actual^2)*sqrt(rho) + 4*rho) + delta_hat2;
            % dP₁ = dP₄ = dP₇ = -1 
            dP1 = -1; dP4 = -1; dP7 = -1;
            % dP₂ = −2√(1−â²) + 2xi_hat
            dP2 = -2*sqrt(1 - a_hat_actual^2) + 2*xi_hat(i);
            % dP₅ = −2√(1−â²+ρ+2√(1−â²)√ρ) + 2xi_hat
            dP5 = -2*sqrt(1 - a_hat_actual^2 + rho + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho)) + 2*xi_hat(i);
            % dP₈ = −2(√(1−â²)+2√ρ) + 2xi_hat
            dP8 = -2*(sqrt(1 - a_hat_actual^2) + 2*sqrt(rho)) + 2*xi_hat(i);
            % dN₁ = −2α(1−P₃·P₂^{−1/2})·dP₁ − α·P₁·P₂^{−3/2}·P₃·dP₂
            dN1 = -2 * alpha_actual * (1 - P3 * P2.^(-0.5)) * (-1) - alpha_actual * P1 * P2.^(-1.5) * P3 * dP2;
            % dN₃ = −2α₁(1−P₆·P₅^{−1/2})·dP₄ − α₁·P₄·P₅^{−3/2}·P₆·dP₅
            dN3 = -2 * alpha1_actual * (1 - P6 * P5.^(-0.5)) * (-1) - alpha1_actual * P4 * P5.^(-1.5) * P6 * dP5;
            % dN₅ = −2α(1−P₉·P₈^{−1/2})·dP₇ − α·P₇·P₈^{−3/2}·P₉·dP₈
            dN5 = -2 * alpha_actual * (1 - P9 * P8.^(-0.5)) * (-1) - alpha_actual * P7 * P8.^(-1.5) * P9 * dP8;
            % 无量纲刚度 K̂(i) = 1 + dN₁ + dN₃ + dN₅
            K_hat(i) = 1 + dN1 + dN3 + dN5;
            f_hat_curve(i) = xi_hat(i) - 2*alpha_actual * P1*(sqrt(P2)-P3)/sqrt(P2) - 2*alpha1_actual * P4*(sqrt(P5)-P6)/sqrt(P5) - 2*alpha_actual * P7*(sqrt(P8)-P9)/sqrt(P8);
            y_hat_curve(i) = xi_hat(i) - x_e_hat;
        end

        y_hat_all{end+1} = y_hat_curve;  
        f_hat_all{end+1} = f_hat_curve;  
        K_hat_all{end+1} = K_hat;
        k1_record(end+1) = k1;

    end
end

if found_count > 0
    %% 第 3 组
    target_idx = 3; 
    
    if target_idx > found_count
        target_idx = found_count;
    end

    figure(1); clf; 
    set(gcf, 'Position', [100, 100, 800, 600]);
    
    yyaxis left     
    plot(y_hat_all{target_idx}, f_hat_all{target_idx}, 'LineWidth', 2); 
    ylabel('Dimensionless Force $\hat{f}$', 'Interpreter', 'latex', 'FontSize', 18);
    ylim([-6, 6]); xlim([-3, 3]);
    grid on;

    yyaxis right    
    plot(y_hat_all{target_idx}, K_hat_all{target_idx}, 'r-', 'LineWidth', 2); 
    ylabel('Dimensionless Stiffness $\hat{K}$', 'Interpreter', 'latex', 'FontSize', 18);
    ylim([0, 1.5]);
    
    title(['Results for Parameter Set No. ', num2str(target_idx)], 'FontSize', 24);
    xlabel('Dimensionless Displacement $\hat{y}$', 'Interpreter', 'latex', 'FontSize', 18);
    
    legend(sprintf('Force'), ...
           sprintf('Stiffness'), ...
           'Interpreter', 'latex', 'Location', 'northwest');
else
    disp('未找到有效参数组合');
end


%% 计算总刚度曲线 [delta_hat, a_hat, gamma]
test_params = [0.700, 0.875, 1.728;
    0.600, 0.805, 1.970;
    0.500, 0.755, 2.143;
%   0.200, 0.800, 2.192;
    0.500, 0.800, 1.987;
    0.800, 0.800, 1.987];

num_test = size(test_params, 1);

base_colors = lines(num_test);
line_styles = {'-', '--', ':', '-.'};
test_styles = cell(1, num_test);
for i = 1:num_test
    style_idx = mod(i-1, length(line_styles)) + 1;
    test_styles{i} = line_styles{style_idx};
end

test_color_specs = cell(1, num_test);
for i = 1:num_test
    rgb = base_colors(i, :);
    test_color_specs{i} = {rgb, test_styles{i}};
end

%% 初始化存储句柄和图例文本
h_targets = gobjects(1, num_test);
target_legends = cell(1, num_test);

fprintf('\n五个无量纲参数计算结果:\n');
fprintf('-------------------------------------------------------------------------------------------\n');
fprintf('  Index  |   delta_hat (δ̂) |   a_hat (â)   |   gamma (γ)   |   alpha (α)   |   alpha1 (α1)\n');
fprintf('-------------------------------------------------------------------------------------------\n');

figure(2); clf; 
set(gcf, 'Position', [100, 100, 800, 600]);
hold on;

for j = 1:size(test_params, 1)
    d_hat = test_params(j,1); a_hat = test_params(j,2); g = test_params(j,3);
    % Δ = √(1 + â²·g² − 2·â²·g)
    Delta = sqrt(1 + a_hat^2*g^2 - 2*a_hat^2*g);
    % Δ₁ = (1 + d̂)·(g − 1)
    Delta1 = (1 + d_hat)*(g - 1);
    % Δ₂ = (1 + d̂)·(g − 1)³
    Delta2 = (1 + d_hat)*(g - 1)^3;
    % C₁ = 6·(1 + d̂)·â⁻³ / [ −12·Δ₂/Δ³ + 72·Δ₂·(1 − â²)/Δ⁵ − 60·Δ₂·(1 − â²)²/Δ⁷ ]
    C1 = 6*(1 + d_hat)* a_hat^(-3)/(-12 * Delta2/Delta^3 + 72*Delta2*(1 - a_hat^2)/Delta^5 - 60*Delta2*(1 - a_hat^2)^2/Delta^7);
    % α₁_calc = −1 / { C₁·[ 4 − 4·Δ₁/Δ + 4·(1 − â²)·Δ₁/Δ³ ] + 2·[ 1 − (1 + d̂)/â ] }
    alpha1_calc = -1/(C1*(4-4*Delta1/Delta + 4*(1-a_hat^2)*Delta1/Delta^3)+ 2*(1-(1+d_hat)/a_hat));
    % α_calc = C₁ · α₁_calc
    alpha_calc = C1 * alpha1_calc;
    % K̂_target = zeros(size(ŷ))
    K_hat_target = zeros(size(y_hat));
    % ρ_target = (1 − â²) / (g − 1)²
    rho_target = (1 - a_hat^2) / (g - 1)^2;
    % δ̂₁_target = 1 − √[ 1 + 2·√(1 − â²)·√ρ_target + ρ_target ] + d̂
    delta_hat1_target = 1 - sqrt(1 + 2*sqrt(1 - a_hat^2)*sqrt(rho_target) + rho_target) + d_hat;
    % δ̂₂_target = 1 − √[ 1 + 4·√(1 − â²)·√ρ_target + 4·ρ_target ] + d̂
    delta_hat2_target = 1 - sqrt(1 + 4*sqrt(1 - a_hat^2)*sqrt(rho_target) + 4*rho_target) + d_hat;
    % x ̂_e_target = √(1 − â²) + √ρ_target
    x_e_hat_target = sqrt(1 - a_hat^2) + sqrt(rho_target);

    for i = 1:length(y_hat)
        % xi_hat(i) = x̂_e_target + ŷ(i)
        xi_hat(i) = x_e_hat_target + y_hat(i);
        % P₁ = √(1 − â²) − xi_hat(i)
        P1 = sqrt(1 - a_hat^2) - xi_hat(i);
        % P₂ = 1 − 2·√(1 − â²)·xi_hat + xi_hat(i)²
        P2 = 1 - 2*sqrt(1 - a_hat^2)*xi_hat(i) + xi_hat(i)^2;
        % P₃ = 1 + d̂
        P3 = 1 + d_hat;
        % P₄ = √(1 − â² + ρ_target + 2·√(1 − â²)·√ρ_target) − xi_hat(i)
        P4 = sqrt(1 - a_hat^2 + rho_target + 2*sqrt(1 - a_hat^2)*sqrt(rho_target)) - xi_hat(i);
        % P₅ = 1 + ρ_target + 2·√(1 − â²)·√ρ_target − 2·√(1 − â² + ρ_target + 2·√(1 − â²)·√ρ_target)·xi_hat + xi_hat(i)²
        P5 = 1 + rho_target + 2*sqrt(1 - a_hat^2)*sqrt(rho_target) - 2*sqrt(1 - a_hat^2 + rho_target + 2*sqrt(1 - a_hat^2)*sqrt(rho_target))*xi_hat(i) + xi_hat(i)^2;
        % P₆ = √(1 + 2·√(1 − â²)·√ρ_target + ρ_target) + δ̂₁_target
        P6 = sqrt(1 + 2*sqrt(1 - a_hat^2)*sqrt(rho_target) + rho_target) + delta_hat1_target;
        % P₇ = √(1 − â²) + 2·√ρ_target − xi_hat(i)
        P7 = sqrt(1 - a_hat^2) + 2*sqrt(rho_target) - xi_hat(i);
        % P₈ = 1 + 4·√(1 − â²)·√ρ_target + 4·ρ_target − 2·(√(1 − â²) + 2·√ρ_target)·xi_hat + xi_hat(i)²
        P8 = 1 + 4*sqrt(1 - a_hat^2)*sqrt(rho_target) + 4*rho_target - 2*(sqrt(1 - a_hat^2) + 2*sqrt(rho_target))*xi_hat(i) + xi_hat(i)^2;
        % P₉ = √(1 + 4·√(1 − â²)·√ρ_target + 4·ρ_target) + δ̂₂_target
        P9 = sqrt(1 + 4*sqrt(1 - a_hat^2)*sqrt(rho_target) + 4*rho_target) + delta_hat2_target;
        % dP₂ = −2·√(1 − â²) + 2·xi_hat
        dP2 = -2*sqrt(1 - a_hat^2) + 2*xi_hat(i);
        % dP₅ = −2·√(1 − â² + ρ_target + 2·√(1 − â²)·√ρ_target) + 2·xi_hat
        dP5 = -2*sqrt(1 - a_hat^2 + rho_target + 2*sqrt(1 - a_hat^2)*sqrt(rho_target)) + 2*xi_hat(i);
        % dP₈ = −2·(√(1 − â²) + 2·√ρ_target) + 2·xi_hat
        dP8 = -2*(sqrt(1 - a_hat^2) + 2*sqrt(rho_target)) + 2*xi_hat(i);
        % dN₁ = −2·α_calc·(1 − P₃·P₂⁻⁰·⁵)·(−1) − α_calc·P₁·P₂⁻¹·⁵·P₃·dP₂
        dN1 = -2 * alpha_calc * (1 - P3 * P2.^(-0.5)) * (-1) - alpha_calc * P1 * P2.^(-1.5) * P3 .* dP2;
        % dN₃ = −2·α₁_calc·(1 − P₆·P₅⁻⁰·⁵)·(−1) − α₁_calc·P₄·P₅⁻¹·⁵·P₆·dP₅
        dN3 = -2 * alpha1_calc * (1 - P6 * P5.^(-0.5)) * (-1) - alpha1_calc * P4 * P5.^(-1.5) * P6 .* dP5;
        % dN₅ = −2·α_calc·(1 − P₉·P₈⁻⁰·⁵)·(−1) − α_calc·P₇·P₈⁻¹·⁵·P₉·dP₈
        dN5 = -2 * alpha_calc * (1 - P9 * P8.^(-0.5)) * (-1) - alpha_calc * P7 * P8.^(-1.5) * P9 .* dP8;
        % K̂_target(i) = 1 + dN₁ + dN₃ + dN₅
        K_hat_target(i) = 1 + dN1 + dN3 + dN5;
    end
    h_targets(j) = plot(y_hat, K_hat_target, 'Color', test_color_specs{j}{1}, ...
        'LineStyle', test_color_specs{j}{2}, 'LineWidth', 3);
    target_legends{j} = sprintf('$\\hat{a}=%.3f, \\hat{\\delta}=%.3f, \\gamma=%.3f, \\alpha=%.3f, \\alpha_1=%.3f$', ...
        a_hat, d_hat, g, alpha_calc, alpha1_calc);
end

% 图例
legend(h_targets, target_legends, ...
    'Interpreter', 'latex', 'Location', 'northeast', 'FontSize', 16);
set(legend, 'Position', [0.45, 0.75, 0.2, 0.1]);
set(gca, 'FontSize', 16);
xlabel('$\hat{y}$', 'Interpreter', 'latex', 'FontSize', 22);
ylabel('$\hat{K}$', 'Interpreter', 'latex', 'FontSize', 22);
xticks([-0.8, -0.5, -0.3, 0, 0.3, 0.5, 0.8]);

title('\textbf{Stiffness curves comparison of QZS}', 'FontSize', 26, 'Interpreter', 'latex');
grid on; box on; xlim([-0.8, 0.8]); ylim([-0, 1.5]);

num_test = size(test_params, 1);
alpha_store = zeros(num_test, 1);
alpha1_store = zeros(num_test, 1);

for j = 1:num_test
    d_hat = test_params(j,1); a_hat = test_params(j,2); g = test_params(j,3);

    % Δ = √(1 + â²·g² − 2·â²·g)
    Delta = sqrt(1 + a_hat^2*g^2 - 2*a_hat^2*g);
    % Δ₁ = (1 + d̂)·(g − 1)
    Delta1 = (1 + d_hat)*(g - 1);
    % Δ₂ = (1 + d̂)·(g − 1)³
    Delta2 = (1 + d_hat)*(g - 1)^3;
    % C₁ = 6·(1 + d̂)·â⁻³ / [ −12·Δ₂/Δ³ + 72·Δ₂·(1 − â²)/Δ⁵ − 60·Δ₂·(1 − â²)²/Δ⁷ ]
    C1 = 6*(1 + d_hat)* a_hat^(-3) / (-12 * Delta2/Delta^3 + 72*Delta2*(1 - a_hat^2)/Delta^5 - 60*Delta2*(1 - a_hat^2)^2/Delta^7);
    % α₁_calc = −1 / { C₁·[ 4 − 4·Δ₁/Δ + 4·(1 − â²)·Δ₁/Δ³ ] + 2·[ 1 − (1 + d̂)/â ] }
    alpha1_calc = -1/(C1*(4-4*Delta1/Delta + 4*(1-a_hat^2)*Delta1/Delta^3)+ 2*(1-(1+d_hat)/a_hat));
    % α_calc = C₁ · α₁_calc
    alpha_calc = C1 * alpha1_calc;
    % α_store(j) = α_calc
    alpha_store(j) = alpha_calc;
    % α₁_store(j) = α₁_calc
    alpha1_store(j) = alpha1_calc;

    fprintf('    %d    |      %.3f      |     %.3f     |     %.3f     |     %.3f     |     %.3f\n', j, d_hat, a_hat, g, alpha_calc, alpha1_calc);
end

%% 全参数组泰勒展开计算 
fprintf('\n无量纲参数的泰勒展开结果:\n');

num_configs = size(test_params, 1);
all_configs = zeros(num_configs, 5); % 存储 [d, a, g, al, al1]

for j = 1:num_configs
    d_raw = test_params(j,1); 
    a_raw = test_params(j,2); 
    g_raw = test_params(j,3);
    
    % 计算理论 alpha (高精度)
    Delta = sqrt(1 + a_raw^2*g_raw^2 - 2*a_raw^2*g_raw);
    Delta1 = (1 + d_raw)*(g_raw - 1);
    Delta2 = (1 + d_raw)*(g_raw - 1)^3;
    C1 = 6*(1 + d_raw)* a_raw^(-3) / (-12 * Delta2/Delta^3 + 72*Delta2*(1 - a_raw^2)/Delta^5 - 60*Delta2*(1 - a_raw^2)^2/Delta^7);
    al1_raw = -1 / (C1 * (4 - 4*Delta1/Delta + 4*(1-a_raw^2)*Delta1/Delta^3) + 2*(1 - (1+d_raw)/a_raw));
    al_raw = C1 * al1_raw;
    
    % 强制截断为3位小数，模拟表格输入
    all_configs(j, :) = [round(d_raw,3), round(a_raw,3), round(g_raw,3), round(al_raw,3), round(al1_raw,3)];
end

% 执行泰勒展开计算
dy_step = 0.00001; 
y_range = [-dy_step, 0, dy_step];

for j = 1:num_configs
    % 提取截断后的参数
    d_t = all_configs(j,1); a_t = all_configs(j,2); g_t = all_configs(j,3);
    al_t = all_configs(j,4); al1_t = all_configs(j,5);
    
    % 中间几何变量计算
    rho_t = (1 - a_t^2) / (g_t - 1)^2;
    xe_t = sqrt(1 - a_t^2) + sqrt(rho_t);
    dh1_t = 1 - sqrt(1 + 2*sqrt(1 - a_t^2)*sqrt(rho_t) + rho_t) + d_t;
    dh2_t = 1 - sqrt(1 + 4*sqrt(1 - a_t^2)*sqrt(rho_t) + 4*rho_t) + d_t;
    
    F_res = zeros(1, 3); K_res = zeros(1, 3);
    for k = 1:3
        yi = y_range(k); xi = xe_t + yi;
        % P参数组
        P1=sqrt(1-a_t^2)-xi; P2=1-2*sqrt(1-a_t^2)*xi+xi^2; P3=1+d_t;
        P4=sqrt(1-a_t^2+rho_t+2*sqrt(1-a_t^2)*sqrt(rho_t))-xi;
        P5=1+rho_t+2*sqrt(1-a_t^2)*sqrt(rho_t)-2*sqrt(1-a_t^2+rho_t+2*sqrt(1-a_t^2)*sqrt(rho_t))*xi+xi^2;
        P6=sqrt(1+2*sqrt(1-a_t^2)*sqrt(rho_t)+rho_t)+dh1_t;
        P7=sqrt(1-a_t^2)+2*sqrt(rho_t)-xi;
        P8=1+4*sqrt(1-a_t^2)*sqrt(rho_t)+4*rho_t-2*(sqrt(1-a_t^2)+2*sqrt(rho_t))*xi+xi^2;
        P9=sqrt(1+4*sqrt(1-a_t^2)*sqrt(rho_t)+4*rho_t)+dh2_t;
        
        % 力平衡方程
        F_res(k) = xi - 2*al_t*P1*(1 - P3/sqrt(P2)) ...
                      - 2*al1_t*P4*(1 - P6/sqrt(P5)) ...
                      - 2*al_t*P7*(1 - P9/sqrt(P8));
        % 刚度（导数）
        dP2 = -2*sqrt(1-a_t^2)+2*xi; dP5 = -2*sqrt(1-a_t^2+rho_t+2*sqrt(1-a_t^2)*sqrt(rho_t))+2*xi;  
        dP8 = -2*(sqrt(1-a_t^2)+2*sqrt(rho_t))+2*xi;
        dN1 = -2*al_t*(1-P3*P2^-0.5)*-1 - al_t*P1*P2^-1.5*P3*dP2;
        dN3 = -2*al1_t*(1-P6*P5^-0.5)*-1 - al1_t*P4*P5^-1.5*P6*dP5;
        dN5 = -2*al_t*(1-P9*P8^-0.5)*-1 - al_t*P7*P8^-1.5*P9*dP8;
        K_res(k) = 1 + dN1 + dN3 + dN5;
    end
    
    % 提取系数
    mu0 = F_res(2); 
    mu1 = K_res(2); 
    mu3 = ((K_res(3) - 2*K_res(2) + K_res(1)) / dy_step^2) / 6;
    
    % 打印输出
    fprintf('Group%d: [δ̂=%.3f, â=%.3f, γ=%.3f, α=%.3f, α₁=%.3f]\n', ...
        j, d_t, a_t, g_t, al_t, al1_t);
    fprintf('  -> 展开式: f_hat = %.6f*y^3 + %.6f*y + %.6f\n\n', mu3, mu1, mu0);
end




%% 传递率曲线计算
% L_ref = sqrt(1^2 + 40^2);
% Ze_mm = 3;                   % 激励幅值 3 mm
% Ze_hat = Ze_mm / L_ref;      % 无量纲激励幅值 ≈ 0.03194
m = 3;              % 实际负载质量 3 kg
g_acc = 9.81;       % 重力加速度 m/s^2
zeta = 0.15;        % 阻尼比
Ze_mm = 3;          % 激励幅值 3 mm

L_ref = sqrt(a^2 + h1^2); % 几何参考长度（米）
Ze_hat = Ze_mm / 1000 / L_ref; % 无量纲激励幅值


%% 所有隔离器的无量纲参数
mu1_one_pair = 0.1907;
mu3_one_pair = 1.3836;
params_one_pair = '$\delta=0.4089,\ \alpha=0.9218,\ \hat{a}=0.9791$';

mu1_three_pair = 0.1188;
mu3_three_pair = 1.2344;
params_three_pair = '$\delta=0.4706,\ \hat{a}=0.9999,\ \alpha=0.4793,\ \alpha_1=0.1786$';

mu1_opt1 = 0.000476;
mu3_opt1 = 0.001705;
params_opt1 = '$\delta=0.500,\ \hat{a}=0.755,\ \gamma=2.143,\ \alpha=0.942,\ \alpha_1=0.501$';

mu1_opt2 = 0.3367;
mu3_opt2 = 0.3876;
params_opt2 = '$\delta=0.700,\ \hat{a}=0.875,\ \gamma=1.728$';
mu_str_opt2 = '$\mu_1=0.3367,\ \mu_3=0.3876$';

mu1_opt3 = 0.2189;
mu3_opt3 = 0.2104;
params_opt3 = '$\delta=0.600,\ \hat{a}=0.805,\ \gamma=1.970$';
mu_str_opt3 = '$\mu_1=0.2189,\ \mu_3=0.2104$';


% 线性系统固有频率
% f0 = 3.5;  % Hz
% 线性系统固有频率
% f0 = 3.5;  % Hz
if found_count > 0
    k1_actual = k1_record(1);  % 使用第一组找到的 k1 值
else
    k1_actual = 1000;  % 默认值，如果没有找到
end
k2_actual = k1_actual / alpha_target;
K_eq = k2_actual * mu1_opt1;
f0 = (1/(2*pi)) * sqrt(K_eq / m);
fprintf('基于3kg负载计算得到的固有频率 f0 = %.2f Hz\n', f0);



%% 传递率计算函数
function Ta = compute_transmissibility(mu1, mu3, Omega, Ze_hat, zeta)
if Omega < 1e-6
    Ta = 1;
    return;
end

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
cos_phi = (0.75 * mu3 * Ze_hat^2 * Z_hat^3 + (mu1 - Omega^2) * Z_hat) / Omega^2;
cos_phi = max(-1, min(1, cos_phi));
Ta = sqrt(1 + 2 * Z_hat * cos_phi + Z_hat^2);
end

%% 频率扫描
f_vec = linspace(0.1, 1000, 5000);
Omega_vec = f_vec / f0;

Ta_one_pair = zeros(size(f_vec));
Ta_three_pair = zeros(size(f_vec));
Ta_opt1 = zeros(size(f_vec));
Ta_opt2 = zeros(size(f_vec));
Ta_opt3 = zeros(size(f_vec));

for i = 1:length(f_vec)
    Omega = Omega_vec(i);
    Ta_one_pair(i) = compute_transmissibility(mu1_one_pair, mu3_one_pair, Omega, Ze_hat, zeta);
    Ta_three_pair(i) = compute_transmissibility(mu1_three_pair, mu3_three_pair, Omega, Ze_hat, zeta);
    Ta_opt1(i) = compute_transmissibility(mu1_opt1, mu3_opt1, Omega, Ze_hat, zeta);
    Ta_opt2(i) = compute_transmissibility(mu1_opt2, mu3_opt2, Omega, Ze_hat, zeta);
    Ta_opt3(i) = compute_transmissibility(mu1_opt3, mu3_opt3, Omega, Ze_hat, zeta);
end

%%  传递率图1: 显示五个无量纲参数
figure('Color', 'w', 'Position', [100, 100, 950, 650]);

h1 = plot(f_vec, Ta_one_pair, 'b--', 'LineWidth', 1.5); hold on;
h2 = plot(f_vec, Ta_three_pair, 'r-', 'LineWidth', 1.5);
h3 = plot(f_vec, Ta_opt1, 'g-.', 'LineWidth', 1.5);
h4 = plot(f_vec, Ta_opt2, 'm:', 'LineWidth', 1.5);
h5 = plot(f_vec, Ta_opt3, 'c-', 'LineWidth', 1.5);

yline(1, 'k:', 'LineWidth', 0.8);

grid on; box on;
set(gca, 'FontSize', 14, 'FontName', 'Times New Roman');
xlabel('Frequency (Hz)', 'FontSize', 22);
ylabel('Transmissibility $T_a$', 'Interpreter', 'latex', 'FontSize', 22, 'FontWeight', 'bold');
title(['\textbf{Displacement Transmissibility ($\zeta = $', num2str(zeta), ', $Z_e = $', num2str(Ze_mm), 'mm)}'], ...
    'Interpreter', 'latex', 'FontSize', 24);

xlim([0, 10]); ylim([0, 12]);
set(gca, 'XTick', 0:2:10, 'YTick', 0:2:12);

legend([h1, h2, h3, h4, h5], ...
    {params_one_pair, params_three_pair, ...
    params_opt1, ...
    params_opt2, ...
    params_opt3}, ...
    'Location', 'northeast', 'FontSize', 15, 'Interpreter', 'latex');
%% 图1的小窗口
axes('Position', [0.60, 0.40, 0.25, 0.25]);
f_inset = linspace(6, 10, 200);
Omega_inset = f_inset / f0;

Ta_one_inset = zeros(size(f_inset));
Ta_three_inset = zeros(size(f_inset));
Ta_opt1_inset = zeros(size(f_inset));
Ta_opt2_inset = zeros(size(f_inset));
Ta_opt3_inset = zeros(size(f_inset));

for i = 1:length(f_inset)
    Omega = Omega_inset(i);
    Ta_one_inset(i) = compute_transmissibility(mu1_one_pair, mu3_one_pair, Omega, Ze_hat, zeta);
    Ta_three_inset(i) = compute_transmissibility(mu1_three_pair, mu3_three_pair, Omega, Ze_hat, zeta);
    Ta_opt1_inset(i) = compute_transmissibility(mu1_opt1, mu3_opt1, Omega, Ze_hat, zeta);
    Ta_opt2_inset(i) = compute_transmissibility(mu1_opt2, mu3_opt2, Omega, Ze_hat, zeta);
    Ta_opt3_inset(i) = compute_transmissibility(mu1_opt3, mu3_opt3, Omega, Ze_hat, zeta);
end

plot(f_inset, Ta_one_inset, 'b--', 'LineWidth', 1.2); hold on;
plot(f_inset, Ta_three_inset, 'r-', 'LineWidth', 1.2);
plot(f_inset, Ta_opt1_inset, 'g-.', 'LineWidth', 1.2);
plot(f_inset, Ta_opt2_inset, 'm:', 'LineWidth', 1.2);
plot(f_inset, Ta_opt3_inset, 'c-', 'LineWidth', 1.2);
grid on;
xlim([6, 10]); ylim([0, 0.25]);
set(gca, 'FontSize', 12, 'FontName', 'Times New Roman');
xlabel('Frequency (Hz)', 'FontSize', 16);
ylabel('$T_a$', 'Interpreter', 'latex', 'FontSize', 16);

%% 传递率图2: 显示 μ₁和μ₃ 取值
figure('Color', 'w', 'Position', [100, 100, 950, 650]);

plot(f_vec, Ta_one_pair, 'b--', 'LineWidth', 1.5); hold on;
plot(f_vec, Ta_three_pair, 'r-', 'LineWidth', 1.5);
plot(f_vec, Ta_opt1, 'g-.', 'LineWidth', 1.5);
plot(f_vec, Ta_opt2, 'm:', 'LineWidth', 1.5);
plot(f_vec, Ta_opt3, 'c-', 'LineWidth', 1.5);

yline(1, 'k:', 'LineWidth', 0.8);

grid on; box on;
set(gca, 'FontSize', 14, 'FontName', 'Times New Roman');
xlabel('Frequency (Hz)', 'FontSize', 22);
ylabel('Transmissibility $T_a$', 'Interpreter', 'latex', 'FontSize', 22, 'FontWeight', 'bold');
title(['\textbf{Displacement Transmissibility ($\zeta = $', num2str(zeta), ', $Z_e = $', num2str(Ze_mm), 'mm)}'], ...
    'Interpreter', 'latex', 'FontSize', 24);

xlim([0, 10]); ylim([0, 12]);
set(gca, 'XTick', 0:2:10, 'YTick', 0:2:12);

legend({sprintf('$\\mu_1=%.4f,\\ \\mu_3=%.4f$', mu1_one_pair, mu3_one_pair), ...
    sprintf('$\\mu_1=%.4f,\\ \\mu_3=%.4f$', mu1_three_pair, mu3_three_pair), ...
    sprintf('$\\mu_1=%.4f,\\ \\mu_3=%.4f$', mu1_opt1, mu3_opt1), ...
    sprintf('$\\mu_1=%.4f,\\ \\mu_3=%.4f$', mu1_opt2, mu3_opt2), ...
    sprintf('$\\mu_1=%.4f,\\ \\mu_3=%.4f$', mu1_opt3, mu3_opt3)}, ...
    'Location', 'northeast', 'FontSize', 15, 'Interpreter', 'latex');

%% 图2的小窗
axes('Position', [0.60, 0.40, 0.25, 0.25]);

plot(f_inset, Ta_one_inset, 'b--', 'LineWidth', 1.2); hold on;
plot(f_inset, Ta_three_inset, 'r-', 'LineWidth', 1.2);
plot(f_inset, Ta_opt1_inset, 'g-.', 'LineWidth', 1.2);
plot(f_inset, Ta_opt2_inset, 'm:', 'LineWidth', 1.2);
plot(f_inset, Ta_opt3_inset, 'c-', 'LineWidth', 1.2);
grid on;
xlim([6, 10]); ylim([0, 0.25]);
set(gca, 'FontSize', 12, 'FontName', 'Times New Roman');
xlabel('Frequency (Hz)', 'FontSize', 16);
ylabel('$T_a$', 'Interpreter', 'latex', 'FontSize', 16);

%% 输出结果
fprintf('\n========== 传递率计算结果 ==========\n');
fprintf('参考频率 f0 = %.1f Hz\n', f0);
fprintf('激励幅值 Z_e = %.1f mm (无量纲: %.4f)\n', Ze_mm, Ze_hat);
fprintf('阻尼比 ζ = %.3f\n\n', zeta);

% 计算指标函数
function [f_peak, Ta_peak, f_iso] = calc_metrics(f_vec, Ta)
[Ta_peak, idx_peak] = max(Ta(2:end));
f_peak = f_vec(idx_peak + 1);
idx_iso = find(Ta < 1, 1);
if isempty(idx_iso)
    f_iso = NaN;
else
    f_iso = f_vec(idx_iso);
end
end

%% 读取CSV文件并计算传递后响应
[filename, filepath] = uigetfile('*.csv', '请选择包含振动数据的CSV文件');
if isequal(filename, 0)
    disp('用户取消选择文件');
    return;
end
fullpath = fullfile(filepath, filename);
fprintf('\n正在读取文件: %s\n', filename);

data = readmatrix(fullpath, 'NumHeaderLines', 3);
t = data(:, 1);
v_raw = data(:, 2);
% 修改增益
gain = 100;
v_in = v_raw / gain;
v_in = v_in - mean(v_in);
dt = t(2) - t(1);
fs = 1 / dt;
fprintf('采样频率: %.2f Hz\n', fs);
N = length(v_in);
freq = (0:N-1) * fs / N;
V_in_fft = fft(v_in);
V_in_mag = abs(V_in_fft) / N * 2;
V_in_mag(1) = V_in_mag(1) / 2;
[~, idx_max] = max(V_in_mag(2:floor(N/2)));
f_excitation = freq(idx_max + 1);
fprintf('主激励频率: %.2f Hz\n', f_excitation);

% 计算完整传递率曲线
n_pos = floor(N/2);
freq_range = freq(1:n_pos);
Omega_range = freq_range / f0;
Ta_curve_all = zeros(5, n_pos);
for j = 1:n_pos
    Ta_curve_all(1, j) = compute_transmissibility(mu1_one_pair, mu3_one_pair, Omega_range(j), Ze_hat, zeta);
    Ta_curve_all(2, j) = compute_transmissibility(mu1_three_pair, mu3_three_pair, Omega_range(j), Ze_hat, zeta);
    Ta_curve_all(3, j) = compute_transmissibility(mu1_opt1, mu3_opt1, Omega_range(j), Ze_hat, zeta);
    Ta_curve_all(4, j) = compute_transmissibility(mu1_opt2, mu3_opt2, Omega_range(j), Ze_hat, zeta);
    Ta_curve_all(5, j) = compute_transmissibility(mu1_opt3, mu3_opt3, Omega_range(j), Ze_hat, zeta);
end
% 在频域应用传递率曲线
v_out_all = zeros(N, 5);
for i = 1:5
    H_full = ones(1, N);
    H_full(1:n_pos) = Ta_curve_all(i, :);
    if mod(N, 2) == 0
        H_full(n_pos+1) = Ta_curve_all(i, n_pos);
        for k = 2:n_pos, H_full(N - k + 2) = conj(Ta_curve_all(i, k)); end
    else
        for k = 2:n_pos, H_full(N - k + 2) = conj(Ta_curve_all(i, k)); end
    end

    if size(V_in_fft, 2) > 1, V_in_fft = V_in_fft(:); end
    V_out_freq = V_in_fft .* H_full(:);
    v_out_all(:, i) = real(ifft(V_out_freq));
end
%% 绘制输入输出对比图
% 定义颜色
colors_map = {[0 0.4470 0.7410], [0.8500 0.3250 0.0980], [0.4660 0.6740 0.1880], [0.4940 0.1840 0.5560], [0.3010 0.7450 0.9330]};

param_names_legend = { ...
    sprintf('One-pair: $\\hat{\\delta}=0.409, \\hat{a}=0.979, \\alpha=0.922$'), ...
    sprintf('Three-pair: $\\hat{\\delta}=0.471, \\hat{a}=1.000, \\alpha=0.479, \\alpha_1=0.179$'), ...
    sprintf('Opt1: $\\hat{\\delta}=0.500, \\hat{a}=0.755, \\gamma=2.143, \\alpha=0.942, \\alpha_1=0.501$'), ...
    sprintf('Opt2: $\\hat{\\delta}=0.700, \\hat{a}=0.875, \\gamma=1.728$'), ...
    sprintf('Opt3: $\\hat{\\delta}=0.600, \\hat{a}=0.805, \\gamma=1.970$')};

time_show = min(2, t(end));
idx_show = t <= time_show;
figure('Color', 'w', 'Position', [100, 100, 950, 650]);

subplot(3, 2, 1);
plot(t(idx_show), v_in(idx_show), '--', 'Color', [0.5, 0.5, 0.5], 'LineWidth', 2);
xlabel('Time (s)', 'Interpreter', 'latex', 'FontSize', 22);
ylabel('Voltage (V)', 'Interpreter', 'latex', 'FontSize', 22);
title('Input Signal', 'FontSize', 18, 'Interpreter', 'latex');
set(gca, 'FontSize', 12); grid on; box on; xlim([0, time_show]);

for i = 1:5
    subplot(3, 2, i+1);
    plot(t(idx_show), v_out_all(idx_show, i), 'Color', colors_map{i}, 'LineWidth', 1.5);
    xlabel('Time (s)', 'Interpreter', 'latex', 'FontSize', 22);
    ylabel('Voltage (V)', 'Interpreter', 'latex', 'FontSize', 22);
    title(sprintf('Output %d', i), 'FontSize', 18, 'Interpreter', 'latex');
    set(gca, 'FontSize', 12); grid on; box on; xlim([0, time_show]);
end
sgtitle('Voltage Response (Time Domain)', 'FontSize', 28, 'FontWeight', 'bold');

figure('Color', 'w', 'Position', [100, 100, 950, 650]);
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
grid on; box on; xlim([0.5, fs/2]); hold off;

%% 保存并结束
output_filename = strrep(filename, '.csv', '_voltage_output.mat');
save(fullfile(filepath, output_filename), 't', 'v_in', 'v_out_all', 'Ta_curve_all', 'f_excitation');

%% PSD计算辅助函数
function psd = compute_psd(signal, window_size, overlap, nfft, fs, window)
signal = signal(:);
data_windowed = buffer(signal, window_size, overlap, 'nodelay');
if size(data_windowed, 2) > 0 && size(data_windowed, 1) < window_size
    data_windowed(:, end) = [];
end
data_windowed = data_windowed .* window;
psd_matrix = zeros(nfft/2, size(data_windowed, 2));
for j = 1:size(data_windowed, 2)
    fft_data = fft(data_windowed(:,j), nfft);
    psd_matrix(:,j) = abs(fft_data(1:nfft/2)).^2 / (fs * nfft);
    psd_matrix(2:end-1,j) = 2 * psd_matrix(2:end-1,j);
end
psd = mean(psd_matrix, 2);
end