clear; clc;

%% 目标无量纲参数
delta_hat_target = 0.5;      % δ̂ = δ / sqrt(a^2 + h1^2)
a_hat_target     = 0.755;    % â = a / sqrt(a^2 + h1^2)
alpha_target     = 0.942;    % α = k1/k2
alpha1_target    = 0.501;    % α₁ = k3/k2
gamma_target     = 2.143;    % γ = h/d
fprintf('目标无量纲参数:\n');
fprintf('  δ̂ = %.3f, â = %.3f, α = %.3f, α₁ = %.3f, γ = %.3f\n\n', ...
    delta_hat_target, a_hat_target, alpha_target, alpha1_target, gamma_target);

%% 物理参数限制（补充实际的一些空间限制）
k1_range = 100:200:900;      % 上斜弹簧刚度 N/m
h_range  = 0.10:0.05:0.30;   % 中间斜弹簧高度 m
h1_range = 0.14:0.05:0.40;   % 上斜弹簧高度 m
fprintf('总组合数: %d\n\n', length(k1_range) * length(h_range) * length(h1_range));
fprintf('遍历结果（物理量已转换为 mm）:\n');
fprintf('========================================================================================================================================================\n');
fprintf(' k1(N/m) | h(mm) | h1(mm) | k2(N/m) | k3(N/m) | a(mm) | d(mm) | delta(mm) | ρ | â实际 | â误差 %% | γ实际 | γ误差 %% | α实际 | α₁实际 | δ̂实际 | δ̂误差 %%\n');
fprintf('--------------------------------------------------------------------------------------------------------------------------------------------------------\n');

figure('Color', 'w', 'Position', [100, 100, 950, 650]);
colors = lines(length(k1_range));
color_idx = 1;
h_iterated = []; 
iter_legend_str = ''; 
y_hat = linspace(-10, 10, 1000); 

for k1 = k1_range
    for h = h_range
        for h1 = h1_range
            % 用目标无量纲参数计算具体的初始条件
            d = h / gamma_target;                          
            a = (a_hat_target / sqrt(1 - a_hat_target^2)) * h1;  
            delta = delta_hat_target * sqrt(a^2 + h1^2);             
            k2 = k1 / alpha_target;                        
            k3 = alpha1_target * k2;    

            % 参数误差
            alpha_actual    = k1 / k2;                      
            alpha1_actual   = k3 / k2;                      
            a_hat_actual    = a / sqrt(a^2 + h1^2);         
            gamma_actual    = h / d;                        
            delta_hat_actual = delta / sqrt(a^2 + h1^2);    
            rho = (1 - a_hat_actual^2) / (gamma_actual - 1)^2;
            
            delta_hat1 = 1 - sqrt(1 + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho) + rho) + delta_hat_actual;
            delta_hat2 = 1 - sqrt(1 + 4*sqrt(1 - a_hat_actual^2)*sqrt(rho) + 4*rho) + delta_hat_actual;
            
            % 打印输出
            err_delta = abs(delta_hat_actual - delta_hat_target) / delta_hat_target * 100;
            fprintf('%8.1f | %5.1f | %5.1f | %7.1f | %7.1f | %5.1f | %5.1f | %9.2f | %.3f |   %.3f   |   %.2f   |    %.3f     |   %.2f   | %.3f | %.3f | %.3f |   %.2f\n', ...
                k1, h*1000, h1*1000, k2, k3, a*1000, d*1000, delta*1000, rho, a_hat_actual, 0, gamma_actual, 0, alpha_actual, alpha1_actual, delta_hat_actual, err_delta);
            
            x_e_hat = sqrt(1 - a_hat_actual^2) + sqrt(rho);
            y_hat = linspace(-10, 10, 1000); 
            K_hat = zeros(size(y_hat));
            
            for i = 1:length(y_hat)
                xi = x_e_hat + y_hat(i);
                P1 = sqrt(1 - a_hat_actual^2) - xi;
                P2 = 1 - 2*sqrt(1 - a_hat_actual^2)*xi + xi^2;
                P3 = 1 + delta_hat_actual;
                P4 = sqrt(1 - a_hat_actual^2 + rho + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho)) - xi;
                P5 = 1 + rho + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho) - 2*sqrt(1 - a_hat_actual^2 + rho + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho))*xi + xi^2;
                P6 = sqrt(1 + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho) + rho) + delta_hat1;
                P7 = sqrt(1 - a_hat_actual^2) + 2*sqrt(rho) - xi;
                P8 = 1 + 4*sqrt(1 - a_hat_actual^2)*sqrt(rho) + 4*rho - 2*(sqrt(1 - a_hat_actual^2) + 2*sqrt(rho))*xi + xi^2;
                P9 = sqrt(1 + 4*sqrt(1 - a_hat_actual^2)*sqrt(rho) + 4*rho) + delta_hat2;
                dP1 = -1; dP4 = -1; dP7 = -1;
                dP2 = -2*sqrt(1 - a_hat_actual^2) + 2*xi;
                dP5 = -2*sqrt(1 - a_hat_actual^2 + rho + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho)) + 2*xi;
                dP8 = -2*(sqrt(1 - a_hat_actual^2) + 2*sqrt(rho)) + 2*xi;
                dN1 = -2 * alpha_actual * (1 - P3 * P2^(-0.5)) * dP1 - alpha_actual * P1 * P2^(-1.5) * P3 * dP2;
                dN3 = -2 * alpha1_actual * (1 - P6 * P5^(-0.5)) * dP4 - alpha1_actual * P4 * P5^(-1.5) * P6 * dP5;
                dN5 = -2 * alpha_actual * (1 - P9 * P8^(-0.5)) * dP7 - alpha_actual * P7 * P8^(-1.5) * P9 * dP8;
                K_hat(i) = 1 + dN1 + dN3 + dN5;
            end
            f_hat = xi - 2 * alpha_actual*P1*(sqrt(P2)-P3)/sqrt(P2) - 2 * alpha1_actual*P4*(sqrt(P5)-P6)/sqrt(P5)- 2 * alpha1_actual*P7*(sqrt(P8)-P9)/sqrt(P8);
            h_line = plot(y_hat, K_hat, 'Color', colors(color_idx,:), 'LineWidth', 3);
            hold on;
            
            if isempty(h_iterated)
            h_iterated = h_line;
            iter_legend_str = sprintf('$\\hat{a}=%.3f, \\hat{\\delta}=%.3f, \\gamma=%.3f, \\alpha=%.3f, \\alpha_1=%.3f$', ...
            a_hat_target, delta_hat_target, gamma_target, alpha_target, alpha1_target);
            end
        end
    end
    color_idx = color_idx + 1;
end

%% 计算总刚度曲线 
test_params = [0.700, 0.875, 1.728;
               0.600, 0.805, 1.970]; 
h_targets = [];
target_legends = {};
test_colors = {'b--', 'r--'}; 

fprintf('\n目标曲线的五个无量纲参数计算结果:\n');
fprintf('-------------------------------------------------------------------------------------------\n');
fprintf('  Index  |   delta_hat (δ̂) |   a_hat (â)   |   gamma (γ)   |   alpha (α)   |   alpha1 (α1)\n');
fprintf('-------------------------------------------------------------------------------------------\n');

h_targets = [];
target_legends = {};
test_colors = {'b--', 'r--'}; 

for j = 1:size(test_params, 1)
    d_hat = test_params(j,1); a_hat = test_params(j,2); g = test_params(j,3);
    
    Delta = sqrt(1 + a_hat^2*g^2 - 2*a_hat^2*g); 
    Delta1 = (1 + d_hat)*(g - 1);
    Delta2 = (1 + d_hat)*(g - 1)^3;
    C1 = 6*(1 + d_hat)* a_hat^(-3)/(-12 * Delta2/Delta^3 + 72*Delta2*(1 - a_hat^2)/Delta^5 - 60*Delta2*(1 - a_hat^2)^2/Delta^7);
    alpha1_calc = -1/(C1*(4-4*Delta1/Delta + 4*(1-a_hat^2)*Delta1/Delta^3)+ 2*(1-(1+d_hat)/a_hat));
    alpha_calc = C1 * alpha1_calc;
    
    K_hat_target = zeros(size(y_hat));
    rho_target = (1 - a_hat^2) / (g - 1)^2;
    delta_hat1_target = 1 - sqrt(1 + 2*sqrt(1 - a_hat^2)*sqrt(rho_target) + rho_target) + d_hat;
    delta_hat2_target = 1 - sqrt(1 + 4*sqrt(1 - a_hat^2)*sqrt(rho_target) + 4*rho_target) + d_hat;
    x_e_hat_target = sqrt(1 - a_hat^2) + sqrt(rho_target);
    
    for i = 1:length(y_hat)
        xi = x_e_hat_target + y_hat(i);
        P1 = sqrt(1 - a_hat^2) - xi; P2 = 1 - 2*sqrt(1 - a_hat^2)*xi + xi^2; P3 = 1 + d_hat;
        P4 = sqrt(1 - a_hat^2 + rho_target + 2*sqrt(1 - a_hat^2)*sqrt(rho_target)) - xi;
        P5 = 1 + rho_target + 2*sqrt(1 - a_hat^2)*sqrt(rho_target) - 2*sqrt(1 - a_hat^2 + rho_target + 2*sqrt(1 - a_hat^2)*sqrt(rho_target))*xi + xi^2;
        P6 = sqrt(1 + 2*sqrt(1 - a_hat^2)*sqrt(rho_target) + rho_target) + delta_hat1_target;
        P7 = sqrt(1 - a_hat^2) + 2*sqrt(rho_target) - xi;
        P8 = 1 + 4*sqrt(1 - a_hat^2)*sqrt(rho_target) + 4*rho_target - 2*(sqrt(1 - a_hat^2) + 2*sqrt(rho_target))*xi + xi^2;
        P9 = sqrt(1 + 4*sqrt(1 - a_hat^2)*sqrt(rho_target) + 4*rho_target) + delta_hat2_target;
        dP2 = -2*sqrt(1 - a_hat^2) + 2*xi;
        dP5 = -2*sqrt(1 - a_hat^2 + rho_target + 2*sqrt(1 - a_hat^2)*sqrt(rho_target)) + 2*xi;
        dP8 = -2*(sqrt(1 - a_hat^2) + 2*sqrt(rho_target)) + 2*xi;
        dN1 = -2 * alpha_calc * (1 - P3 * P2^(-0.5)) * (-1) - alpha_calc * P1 * P2^(-1.5) * P3 * dP2;
        dN3 = -2 * alpha1_calc * (1 - P6 * P5^(-0.5)) * (-1) - alpha1_calc * P4 * P5^(-1.5) * P6 * dP5;
        dN5 = -2 * alpha_calc * (1 - P9 * P8^(-0.5)) * (-1) - alpha_calc * P7 * P8^(-1.5) * P9 * dP8;
        K_hat_target(i) = 1 + dN1 + dN3 + dN5;
    end
    h_targets(j) = plot(y_hat, K_hat_target, test_colors{j}, 'LineWidth', 3);
    target_legends{j} = sprintf('$\\hat{a}=%.3f, \\hat{\\delta}=%.3f, \\gamma=%.3f, \\alpha=%.3f, \\alpha_1=%.3f$', ...
    a_hat, d_hat, g, alpha_calc, alpha1_calc);
end

% 图例
legend([h_targets, h_iterated], [target_legends, {iter_legend_str}], ...
    'Interpreter', 'latex', 'Location', 'northeast', 'FontSize', 16);
set(legend, 'Position', [0.45, 0.75, 0.2, 0.1]);
set(h_iterated, 'Color', [0.4660 0.6740 0.1880], 'LineStyle', '-', 'LineWidth', 3);
set(gca, 'FontSize', 16);
xlabel('$\hat{y}$', 'Interpreter', 'latex', 'FontSize', 22);
ylabel('$\hat{K}$', 'Interpreter', 'latex', 'FontSize', 22);
xticks([-0.8, -0.5, -0.3, 0, 0.3, 0.5, 0.8]);

title('Stiffness curves comparison of QZS', 'FontSize', 26, 'Interpreter', 'latex');
grid on; box on; xlim([-0.8, 0.8]); ylim([-0, 1.5]);

for j = 1:size(test_params, 1)
    d_hat = test_params(j,1); a_hat = test_params(j,2); g = test_params(j,3);
    
    Delta = sqrt(1 + a_hat^2*g^2 - 2*a_hat^2*g); 
    Delta1 = (1 + d_hat)*(g - 1);
    Delta2 = (1 + d_hat)*(g - 1)^3;

    C1_denom = -12 * Delta2/Delta^3 + 72*Delta2*(1 - a_hat^2)/Delta^5 - 60*Delta2*(1 - a_hat^2)^2/Delta^7;
    C1 = 6*(1 + d_hat)* a_hat^(-3) / C1_denom;
    
    alpha1_calc = -1 / (C1 * (4 - 4*Delta1/Delta + 4*(1-a_hat^2)*Delta1/Delta^3) + 2*(1 - (1+d_hat)/a_hat));
    alpha_calc = C1 * alpha1_calc;

    fprintf('    %d    |      %.3f      |     %.3f     |     %.3f     |     %.3f     |     %.3f\n', j, d_hat, a_hat, g, alpha_calc, alpha1_calc);
end

%% 全参数组泰勒展开计算
fprintf('所有无量纲参数组的泰勒展开结果 (y=0 处):\n');

% 1. 汇总所有待计算的参数组 [delta_hat, a_hat, gamma, alpha, alpha1]
all_configs = [delta_hat_target, a_hat_target, gamma_target, alpha_target, alpha1_target; 
               test_params(1,1), test_params(1,2), test_params(1,3), 0, 0;              
               test_params(2,1), test_params(2,2), test_params(2,3), 0, 0]; 

config_names = {'User Defined Target', 'Test Params Index 1', 'Test Params Index 2'};
dy_step = 0.00001; 
y_range = [-dy_step, 0, dy_step];

mu1_all = zeros(1, 3);
mu3_all = zeros(1, 3);

for j = 1:size(all_configs, 1)
    d_t = all_configs(j,1); a_t = all_configs(j,2); g_t = all_configs(j,3);
    
    if all_configs(j,4) == 0
        Delta = sqrt(1 + a_t^2*g_t^2 - 2*a_t^2*g_t); 
        Delta1 = (1 + d_t)*(g_t - 1);
        Delta2 = (1 + d_t)*(g_t - 1)^3;
        C1_denom = -12 * Delta2/Delta^3 + 72*Delta2*(1 - a_t^2)/Delta^5 - 60*Delta2*(1 - a_t^2)^2/Delta^7;
        C1 = 6*(1 + d_t)* a_t^(-3) / C1_denom;
        al1_t = -1 / (C1 * (4 - 4*Delta1/Delta + 4*(1-a_t^2)*Delta1/Delta^3) + 2*(1 - (1+d_t)/a_t));
        al_t = C1 * al1_t;
    else
        al_t = all_configs(j,4); al1_t = all_configs(j,5);
    end
    
    rho_t = (1 - a_t^2) / (g_t - 1)^2;
    xe_t = sqrt(1 - a_t^2) + sqrt(rho_t);
    dh1_t = 1 - sqrt(1 + 2*sqrt(1 - a_t^2)*sqrt(rho_t) + rho_t) + d_t;
    dh2_t = 1 - sqrt(1 + 4*sqrt(1 - a_t^2)*sqrt(rho_t) + 4*rho_t) + d_t;
    K_res = zeros(1, 3); F_res = zeros(1, 3);

    for k = 1:3
        yi = y_range(k); xi = xe_t + yi;
        P1=sqrt(1-a_t^2)-xi; P2=1-2*sqrt(1-a_t^2)*xi+xi^2; P3=1+d_t;
        P4=sqrt(1-a_t^2+rho_t+2*sqrt(1-a_t^2)*sqrt(rho_t))-xi;
        P5=1+rho_t+2*sqrt(1-a_t^2)*sqrt(rho_t)-2*sqrt(1-a_t^2+rho_t+2*sqrt(1-a_t^2)*sqrt(rho_t))*xi+xi^2;
        P6=sqrt(1+2*sqrt(1-a_t^2)*sqrt(rho_t)+rho_t)+dh1_t;
        P7=sqrt(1-a_t^2)+2*sqrt(rho_t)-xi;
        P8=1+4*sqrt(1-a_t^2)*sqrt(rho_t)+4*rho_t-2*(sqrt(1-a_t^2)+2*sqrt(rho_t))*xi+xi^2;
        P9=sqrt(1+4*sqrt(1-a_t^2)*sqrt(rho_t)+4*rho_t)+dh2_t;
        
        F_res(k) = xi - 2*al_t*P1*(1 - P3/sqrt(P2)) ...
                      - 2*al1_t*P4*(1 - P6/sqrt(P5)) ...
                      - 2*al_t*P7*(1 - P9/sqrt(P8));
        
        dP2 = -2*sqrt(1-a_t^2)+2*xi;  
        dP5 = -2*sqrt(1-a_t^2+rho_t+2*sqrt(1-a_t^2)*sqrt(rho_t))+2*xi;  
        dP8 = -2*(sqrt(1-a_t^2)+2*sqrt(rho_t))+2*xi;
        dN1_t = -2*al_t*(1-P3*P2^-0.5)*-1 - al_t*P1*P2^-1.5*P3*dP2;
        dN3_t = -2*al1_t*(1-P6*P5^-0.5)*-1 - al1_t*P4*P5^-1.5*P6*dP5;
        dN5_t = -2*al_t*(1-P9*P8^-0.5)*-1 - al_t*P7*P8^-1.5*P9*dP8;
        K_res(k) = 1 + dN1_t + dN3_t + dN5_t;
    end

    mu0_val = F_res(2); 
    mu1_val = K_res(2); 
    mu3_val = ((K_res(3) - 2*K_res(2) + K_res(1)) / dy_step^2) / 6;
    
    mu1_all(j) = mu1_val;
    mu3_all(j) = mu3_val;

    fprintf('组别 %d: %s\n', j, config_names{j});
    fprintf('  -> 展开式: f_hat = %.6f*y^3 + %.6f*y + %.6f\n', mu3_val, mu1_val, mu0_val);
end

%% 整理三组参数数据
% 每行对应一组: [delta_hat, a_hat, gamma, alpha, alpha1]
configs = [
    delta_hat_target, a_hat_target, gamma_target, alpha_target, alpha1_target; 
    test_params(1,1), test_params(1,2), test_params(1,3), 0, 0;            
    test_params(2,1), test_params(2,2), test_params(2,3), 0, 0           
];

final_params = zeros(3, 5);
mu1_vals = [mu1_all(1), mu1_all(2), mu1_all(3)]; 
mu3_vals = [mu3_all(1), mu3_all(2), mu3_all(3)];

for j = 1:3
    d_t = configs(j,1); a_t = configs(j,2); g_t = configs(j,3);
    if configs(j,4) == 0 
        Delta = sqrt(1 + a_t^2*g_t^2 - 2*a_t^2*g_t); 
        Delta1 = (1 + d_t)*(g_t - 1);
        Delta2 = (1 + d_t)*(g_t - 1)^3;
        C1_denom = -12 * Delta2/Delta^3 + 72*Delta2*(1 - a_t^2)/Delta^5 - 60*Delta2*(1 - a_t^2)^2/Delta^7;
        C1 = 6*(1 + d_t)* a_t^(-3) / C1_denom;
        al1_t = -1 / (C1 * (4 - 4*Delta1/Delta + 4*(1-a_t^2)*Delta1/Delta^3) + 2*(1 - (1+d_t)/a_t));
        al_t = C1 * al1_t;
    else
        al_t = configs(j,4); al1_t = configs(j,5);
    end
    final_params(j, :) = [d_t, a_t, g_t, al_t, al1_t];
end


%% 传递率曲线计算
L_ref = sqrt(1^2 + 40^2);  
Ze_mm = 3;                   % 激励幅值 3 mm
Ze_hat = Ze_mm / L_ref;      % 无量纲激励幅值 ≈ 0.03194

% 阻尼比
zeta = 0.15;

% 线性系统固有频率
f0 = 3.5;  % Hz

%% 所有隔离器的无量纲参数
mu1_one_paper = 0.1907;
mu3_one_paper = 1.3836;
params_one_paper = '$\delta=0.4089,\ \alpha=0.9218,\ \hat{a}=0.9791$';

mu1_three_paper = 0.1188;
mu3_three_paper = 1.2344;
params_three_paper = '$\delta=0.4706,\ \hat{a}=0.9999,\ \alpha=0.4793,\ \alpha_1=0.1786$';

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

Ta_one_paper = zeros(size(f_vec));
Ta_three_paper = zeros(size(f_vec));
Ta_opt1 = zeros(size(f_vec));
Ta_opt2 = zeros(size(f_vec));
Ta_opt3 = zeros(size(f_vec));

for i = 1:length(f_vec)
    Omega = Omega_vec(i);
    Ta_one_paper(i) = compute_transmissibility(mu1_one_paper, mu3_one_paper, Omega, Ze_hat, zeta);
    Ta_three_paper(i) = compute_transmissibility(mu1_three_paper, mu3_three_paper, Omega, Ze_hat, zeta);
    Ta_opt1(i) = compute_transmissibility(mu1_opt1, mu3_opt1, Omega, Ze_hat, zeta);
    Ta_opt2(i) = compute_transmissibility(mu1_opt2, mu3_opt2, Omega, Ze_hat, zeta);
    Ta_opt3(i) = compute_transmissibility(mu1_opt3, mu3_opt3, Omega, Ze_hat, zeta);
end

%%  图1: 显示五个无量纲参数
figure('Color', 'w', 'Position', [100, 100, 950, 650]);

h1 = plot(f_vec, Ta_one_paper, 'b--', 'LineWidth', 1.5); hold on;
h2 = plot(f_vec, Ta_three_paper, 'r-', 'LineWidth', 1.5);
h3 = plot(f_vec, Ta_opt1, 'g-.', 'LineWidth', 1.5);
h4 = plot(f_vec, Ta_opt2, 'm:', 'LineWidth', 1.5);
h5 = plot(f_vec, Ta_opt3, 'c-', 'LineWidth', 1.5);

yline(1, 'k:', 'LineWidth', 0.8);

grid on; box on;
set(gca, 'FontSize', 14, 'FontName', 'Times New Roman');
xlabel('Frequency (Hz)', 'FontSize', 22, 'FontWeight', 'bold');
ylabel('Transmissibility $T_a$', 'Interpreter', 'latex', 'FontSize', 22, 'FontWeight', 'bold');
title(['Displacement Transmissibility ($\zeta = $', num2str(zeta), ', $Z_e = $', num2str(Ze_mm), 'mm)'], ...
    'Interpreter', 'latex', 'FontSize', 24, 'FontWeight', 'bold');

xlim([0, 10]); ylim([0, 12]);
set(gca, 'XTick', 0:2:10, 'YTick', 0:2:12);

legend([h1, h2, h3, h4, h5], ...
    {params_one_paper, params_three_paper, ...
     sprintf('$\\hat{\\delta}=%.3f,\\ \\hat{a}=%.3f,\\ \\gamma=%.3f,\\ \\alpha=%.3f,\\ \\alpha_1=%.3f$', ...
        configs(1,1), configs(1,2), configs(1,3), configs(1,4), configs(1,5)), ...
     sprintf('$\\hat{\\delta}=%.3f,\\ \\hat{a}=%.3f,\\ \\gamma=%.3f,\\ \\alpha=%.3f,\\ \\alpha_1=%.3f$', ...
        configs(2,1), configs(2,2), configs(2,3), final_params(2,4), final_params(2,5)), ...
     sprintf('$\\hat{\\delta}=%.3f,\\ \\hat{a}=%.3f,\\ \\gamma=%.3f,\\ \\alpha=%.3f,\\ \\alpha_1=%.3f$', ...
        configs(3,1), configs(3,2), configs(3,3), final_params(3,4), final_params(3,5))}, ...
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
    Ta_one_inset(i) = compute_transmissibility(mu1_one_paper, mu3_one_paper, Omega, Ze_hat, zeta);
    Ta_three_inset(i) = compute_transmissibility(mu1_three_paper, mu3_three_paper, Omega, Ze_hat, zeta);
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

%% 图2: 显示 μ₁ 和 μ₃ 取值 
figure('Color', 'w', 'Position', [100, 100, 950, 650]);

plot(f_vec, Ta_one_paper, 'b--', 'LineWidth', 1.5); hold on;
plot(f_vec, Ta_three_paper, 'r-', 'LineWidth', 1.5);
plot(f_vec, Ta_opt1, 'g-.', 'LineWidth', 1.5);
plot(f_vec, Ta_opt2, 'm:', 'LineWidth', 1.5);
plot(f_vec, Ta_opt3, 'c-', 'LineWidth', 1.5);

yline(1, 'k:', 'LineWidth', 0.8);

grid on; box on;
set(gca, 'FontSize', 14, 'FontName', 'Times New Roman');
xlabel('Frequency (Hz)', 'FontSize', 22, 'FontWeight', 'bold');
ylabel('Transmissibility $T_a$', 'Interpreter', 'latex', 'FontSize', 22, 'FontWeight', 'bold');
title(['Displacement Transmissibility ($\zeta = $', num2str(zeta), ', $Z_e = $', num2str(Ze_mm), 'mm)'], ...
    'Interpreter', 'latex', 'FontSize', 24, 'FontWeight', 'bold');

xlim([0, 1000]); ylim([0, 12]);
set(gca, 'XTick', 0:2:10, 'YTick', 0:2:12);

legend({sprintf('$\\mu_1=%.4f,\\ \\mu_3=%.4f$', mu1_one_paper, mu3_one_paper), ...
        sprintf('$\\mu_1=%.4f,\\ \\mu_3=%.4f$', mu1_three_paper, mu3_three_paper), ...
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







%% ==================== 5. 读取CSV文件并计算传递后响应 ====================

% 弹框选择CSV文件
[filename, filepath] = uigetfile('*.csv', '请选择包含振动数据的CSV文件');
if isequal(filename, 0)
    disp('用户取消选择文件');
    return;
end

fullpath = fullfile(filepath, filename);
fprintf('\n正在读取文件: %s\n', filename);

% 读取CSV文件（前三行为标题）
data = readmatrix(fullpath, 'NumHeaderLines', 3);
t = data(:, 1);          % 第一列：时间
v_in = data(:, 2);       % 第二列：电压值（输入信号）

% 假设电压值与位移成线性关系，这里需要根据实际传感器标定进行转换
% 如果没有标定，可以假设比例系数为1
sensitivity = 1.0;  % 灵敏度，单位：V/mm（需要根据实际情况修改）
x_in = v_in * sensitivity;  % 输入位移

% 去除直流分量
x_in = x_in - mean(x_in);

% 采样频率
dt = t(2) - t(1);
fs = 1 / dt;
fprintf('采样频率: %.2f Hz\n', fs);

% 对输入信号进行FFT分析
N = length(x_in);
fprintf('信号长度 N = %d\n', N);
freq = (0:N-1) * fs / N;
X_in = fft(x_in);
X_in_mag = abs(X_in) / N * 2;
X_in_mag(1) = X_in_mag(1) / 2;  % 修正直流分量

% 找到主激励频率（取幅值最大的频率，排除直流分量）
[~, idx_max] = max(X_in_mag(2:floor(N/2)));
f_excitation = freq(idx_max + 1);
fprintf('主激励频率: %.2f Hz\n', f_excitation);

% ========== 计算完整传递率曲线（频率响应函数）==========
% 只计算正频率部分（包括直流）
n_pos = floor(N/2);
freq_range = freq(1:n_pos);  % 正频率
Omega_range = freq_range / f0;  % 无量纲频率

fprintf('正频率点数 n_pos = %d\n', n_pos);

% 为每个参数组计算完整的传递率曲线
Ta_curve_all = zeros(5, n_pos);
fprintf('\n正在计算各参数组的频率响应函数...\n');

% 参数组1: One-paper
for j = 1:n_pos
    Ta_curve_all(1, j) = compute_transmissibility(mu1_one_paper, mu3_one_paper, Omega_range(j), Ze_hat, zeta);
end

% 参数组2: Three-paper
for j = 1:n_pos
    Ta_curve_all(2, j) = compute_transmissibility(mu1_three_paper, mu3_three_paper, Omega_range(j), Ze_hat, zeta);
end

% 参数组3: Opt1 (您的目标参数)
for j = 1:n_pos
    Ta_curve_all(3, j) = compute_transmissibility(mu1_opt1, mu3_opt1, Omega_range(j), Ze_hat, zeta);
end

% 参数组4: Opt2
for j = 1:n_pos
    Ta_curve_all(4, j) = compute_transmissibility(mu1_opt2, mu3_opt2, Omega_range(j), Ze_hat, zeta);
end

% 参数组5: Opt3
for j = 1:n_pos
    Ta_curve_all(5, j) = compute_transmissibility(mu1_opt3, mu3_opt3, Omega_range(j), Ze_hat, zeta);
end

fprintf('频率响应函数计算完成\n');

% ========== 在频域应用传递率曲线 ==========
x_out_all = zeros(N, 5);

for i = 1:5
    % 创建频率响应函数向量
    H_full = ones(1, N);
    
    % 设置正频率部分的传递率
    H_full(1:n_pos) = Ta_curve_all(i, :);
    
    % 设置负频率部分（共轭对称）
    if mod(N, 2) == 0
        % N为偶数
        H_full(n_pos+1) = Ta_curve_all(i, n_pos);  % 奈奎斯特频率
        for k = 2:n_pos
            H_full(N - k + 2) = conj(Ta_curve_all(i, k));
        end
    else
        % N为奇数
        for k = 2:n_pos
            H_full(N - k + 2) = conj(Ta_curve_all(i, k));
        end
    end
    
    % 确保都是列向量
    if size(X_in, 2) > 1
        X_in = X_in(:);
    end
    if size(H_full, 2) > 1
        H_full = H_full(:);
    end
    
    % 频域滤波
    X_out_freq = X_in .* H_full;
    
    % IFFT得到时域输出
    x_out_all(:, i) = real(ifft(X_out_freq));
end

% 计算各个参数组在主激励频率处的传递率（用于参考）
Ta_at_excitation = zeros(1, 5);
for i = 1:5
    % 找到最接近激励频率的频率点
    [~, idx] = min(abs(freq_range - f_excitation));
    Ta_at_excitation(i) = Ta_curve_all(i, idx);
end

fprintf('\n各参数组在主激励频率 %.2f Hz 处的传递率:\n', f_excitation);
fprintf('  One-paper:   %.4f (%.1f dB)\n', Ta_at_excitation(1), 20*log10(Ta_at_excitation(1)));
fprintf('  Three-paper: %.4f (%.1f dB)\n', Ta_at_excitation(2), 20*log10(Ta_at_excitation(2)));
fprintf('  Opt1:        %.4f (%.1f dB)\n', Ta_at_excitation(3), 20*log10(Ta_at_excitation(3)));
fprintf('  Opt2:        %.4f (%.1f dB)\n', Ta_at_excitation(4), 20*log10(Ta_at_excitation(4)));
fprintf('  Opt3:        %.4f (%.1f dB)\n', Ta_at_excitation(5), 20*log10(Ta_at_excitation(5)));

%% ==================== 6. 绘制输入输出对比图 ====================

% 定义统一的参数名称（用于图例）
param_names_legend = { ...
    sprintf('One-paper: $\\delta=0.4089,\\ \\alpha=0.9218,\\ \\hat{a}=0.9791$'), ...
    sprintf('Three-paper: $\\delta=0.4706,\\ \\hat{a}=0.9999,\\ \\alpha=0.4793,\\ \\alpha_1=0.1786$'), ...
    sprintf('Opt1: $\\hat{\\delta}=%.3f,\\ \\hat{a}=%.3f,\\ \\gamma=%.3f,\\ \\alpha=%.3f,\\ \\alpha_1=%.3f$', ...
        configs(1,1), configs(1,2), configs(1,3), configs(1,4), configs(1,5)), ...
    sprintf('Opt2: $\\hat{\\delta}=%.3f,\\ \\hat{a}=%.3f,\\ \\gamma=%.3f,\\ \\alpha=%.3f,\\ \\alpha_1=%.3f$', ...
        configs(2,1), configs(2,2), configs(2,3), final_params(2,4), final_params(2,5)), ...
    sprintf('Opt3: $\\hat{\\delta}=%.3f,\\ \\hat{a}=%.3f,\\ \\gamma=%.3f,\\ \\alpha=%.3f,\\ \\alpha_1=%.3f$', ...
        configs(3,1), configs(3,2), configs(3,3), final_params(3,4), final_params(3,5))};

% 图3：时域对比（显示前2秒或更短时间）
time_show = min(2, t(end));
idx_show = t <= time_show;

figure('Color', 'w', 'Position', [100, 100, 1200, 800]);

% 子图1：输入信号
subplot(3, 2, 1);
plot(t(idx_show), x_in(idx_show), 'b-', 'LineWidth', 1.5);
xlabel('Time (s)', 'FontSize', 14);
ylabel('Displacement (mm)', 'FontSize', 14);
title(sprintf('Input Signal (RMS: %.3f mm)', sqrt(mean(x_in.^2))), 'FontSize', 14, 'FontWeight', 'bold');
grid on; box on;
xlim([0, time_show]);

% 子图2-6：各参数组的输出信号
for i = 1:5
    subplot(3, 2, i+1);
    x_out_rms = sqrt(mean(x_out_all(:, i).^2));
    plot(t(idx_show), x_out_all(idx_show, i), 'LineWidth', 1.5);
    xlabel('Time (s)', 'FontSize', 14);
    ylabel('Displacement (mm)', 'FontSize', 14);
    title(sprintf('Output %d (RMS: %.3f mm, Reduction: %.1f dB)', ...
        i, x_out_rms, 20*log10(x_out_rms/sqrt(mean(x_in.^2)))), ...
        'FontSize', 11);
    grid on; box on;
    xlim([0, time_show]);
end

sgtitle('Input and Output Responses Comparison (Time Domain)', 'FontSize', 18, 'FontWeight', 'bold');

% 图4：频域对比 - 所有PSD曲线画在一张图上（参考您提供的代码）
figure('Color', 'w', 'Position', [100, 100, 1000, 700]);

% 定义窗口参数（用于PSD计算）
window_time = 1;  % 窗口时长 1秒
window_size = window_time * fs;
nfft = 2^nextpow2(window_size);
overlap = nfft/2;  % 50%重叠
f_psd = (0:nfft/2-1)*fs/nfft;

% 计算输入信号的PSD
fprintf('\n正在计算PSD...\n');

% Hanning窗（能量归一化）
window = hann(window_size);
window = window ./ sqrt(mean(window.^2));

% 输入信号PSD
x_in_psd = compute_psd(x_in, window_size, overlap, nfft, fs, window);
loglog(f_psd, sqrt(x_in_psd), 'k-', 'LineWidth', 2, 'DisplayName', 'Input Signal');
hold on;

% 颜色定义
colors_plot = {'b-', 'r-', 'g-', 'm-', 'c-'};

% 计算各参数组输出信号的PSD
for i = 1:5
    x_out_psd = compute_psd(x_out_all(:, i), window_size, overlap, nfft, fs, window);
    loglog(f_psd, sqrt(x_out_psd), colors_plot{i}, 'LineWidth', 1.5, ...
        'DisplayName', sprintf('Group %d: %s', i, param_names_legend{i}));
end

% 设置图形属性
xlabel('Frequency (Hz)', 'FontSize', 16, 'FontWeight', 'bold');
ylabel('PSD [mm/√Hz]', 'FontSize', 16, 'FontWeight', 'bold');
title('Power Spectrum Density Comparison', 'FontSize', 18, 'FontWeight', 'bold');
legend('Location', 'best', 'Interpreter', 'latex', 'FontSize', 8);
grid on; box on;
xlim([0.1, fs/2]);  % 从0.1Hz开始，避免直流分量
ylim auto;

hold off;

% 图5：所有输出叠加对比（时域）
figure('Color', 'w', 'Position', [100, 100, 1000, 600]);

for i = 1:5
    x_out_rms = sqrt(mean(x_out_all(:, i).^2));
    plot(t(idx_show), x_out_all(idx_show, i), colors_plot{i}, 'LineWidth', 1.5, ...
        'DisplayName', sprintf('Group %d: %s (RMS: %.3f mm)', i, param_names_legend{i}, x_out_rms));
    hold on;
end
plot(t(idx_show), x_in(idx_show), 'k--', 'LineWidth', 2, ...
    'DisplayName', sprintf('Input (RMS: %.3f mm)', sqrt(mean(x_in.^2))));
xlabel('Time (s)', 'FontSize', 14);
ylabel('Displacement (mm)', 'FontSize', 14);
title('All Output Responses Comparison', 'FontSize', 16, 'FontWeight', 'bold');
legend('Location', 'best', 'Interpreter', 'latex', 'FontSize', 8);
grid on; box on;
xlim([0, time_show]);

%% ==================== 7. 计算并输出性能指标 ====================

fprintf('\n========== 各参数组性能指标 ==========\n');
fprintf('%-20s %-12s %-12s %-12s %-15s %-12s\n', ...
    'Parameter', 'Ta@f_ex', 'Ta_peak', 'f_iso(Hz)', 'RMS_ratio', 'Reduction(dB)');
fprintf('%-20s %-12s %-12s %-12s %-15s %-12s\n', ...
    '--------------------', '------------', '------------', '------------', '---------------', '------------');

% 计算输入信号的RMS
x_in_rms = sqrt(mean(x_in.^2));

% 重新计算传递率曲线用于性能指标
f_plot = linspace(0.1, 10, 500);
Omega_plot = f_plot / f0;
Ta_plot = zeros(5, length(f_plot));

for j = 1:length(f_plot)
    Ta_plot(1, j) = compute_transmissibility(mu1_one_paper, mu3_one_paper, Omega_plot(j), Ze_hat, zeta);
    Ta_plot(2, j) = compute_transmissibility(mu1_three_paper, mu3_three_paper, Omega_plot(j), Ze_hat, zeta);
    Ta_plot(3, j) = compute_transmissibility(mu1_opt1, mu3_opt1, Omega_plot(j), Ze_hat, zeta);
    Ta_plot(4, j) = compute_transmissibility(mu1_opt2, mu3_opt2, Omega_plot(j), Ze_hat, zeta);
    Ta_plot(5, j) = compute_transmissibility(mu1_opt3, mu3_opt3, Omega_plot(j), Ze_hat, zeta);
end

for i = 1:5
    % 计算输出RMS
    x_out_rms = sqrt(mean(x_out_all(:, i).^2));
    rms_ratio = x_out_rms / x_in_rms;
    
    % 计算总衰减（dB）
    total_reduction = 20 * log10(rms_ratio);
    
    % 获取传递率峰值和隔离频率
    Ta_curve = Ta_plot(i, :);
    [Ta_peak, idx_peak] = max(Ta_curve(2:end));
    f_peak = f_plot(idx_peak + 1);
    idx_iso = find(Ta_curve < 1, 1);
    if isempty(idx_iso)
        f_iso = NaN;
    else
        f_iso = f_plot(idx_iso);
    end
    
    % 获取激励频率处的传递率
    [~, idx_ex] = min(abs(f_plot - f_excitation));
    Ta_at_fex = Ta_curve(idx_ex);
    
    param_names_perf = {'One-paper', 'Three-paper', 'Opt1', 'Opt2', 'Opt3'};
    fprintf('%-20s %-12.4f %-12.4f %-12.2f %-15.4f %-12.2f\n', ...
        param_names_perf{i}, Ta_at_fex, Ta_peak, f_iso, rms_ratio, total_reduction);
end

fprintf('\n========== 隔振效果评估 ==========\n');
fprintf('注：\n');
fprintf('  - RMS比值 < 1 表示有隔振效果\n');
fprintf('  - 衰减值负值越大，隔振效果越好\n');
fprintf('  - 传递率 < 1 的频率范围即为隔振频带\n');

% 保存输出数据
output_filename = strrep(filename, '.csv', '_isolated_output.mat');
save(fullfile(filepath, output_filename), 't', 'x_in', 'x_out_all', 'param_names_legend', ...
    'Ta_curve_all', 'Ta_plot', 'f_plot', 'f_excitation', 'Ta_at_excitation', 'f_psd', 'x_in_psd');
fprintf('\n输出数据已保存至: %s\n', output_filename);
fprintf('程序运行完成！\n');

%% ==================== PSD计算辅助函数 ====================
function psd = compute_psd(signal, window_size, overlap, nfft, fs, window)
    % 分帧
    data_windowed = buffer(signal, window_size, overlap, 'nodelay');
    
    % 去除最后一帧如果长度不足
    if size(data_windowed, 2) > 0 && size(data_windowed, 1) < window_size
        data_windowed(:, end) = [];
    end
    
    % 加窗
    data_windowed = data_windowed .* window;
    
    % 计算PSD
    psd = zeros(nfft/2, size(data_windowed, 2));
    for j = 1:size(data_windowed, 2)
        fft_data = fft(data_windowed(:,j), nfft);
        psd(:,j) = abs(fft_data(1:nfft/2)).^2 / (fs * nfft);
        psd(2:end-1,j) = 2 * psd(2:end-1,j);  % 单边谱修正
    end
    
    % 平均
    psd = mean(psd, 2);
end