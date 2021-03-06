# %%
# from Users.henry.Python Files.Electrical Conductivity SIMS Data.NS_ConductivityOlivines import Sample_Interpolate
# import Fe_Mg_Diffusion_Convolution
import numpy as np
from matplotlib import pyplot as plt
import pandas as pd
from pathlib import Path
import scipy.interpolate as interp
from matplotlib.backends.backend_pdf import PdfPages


from pykrige import OrdinaryKriging


#%%

excel_path = "/Users/henry/Documents/Research/Mantle Xenoliths/AZ18 Samples/Microprobe July 2020/Final Microprobe Data/AB+HT_EMPA_July_2020_SIMS-Mounts_HenrysSamples.xlsx"

Ol_Profiles = pd.read_excel(
    excel_path,
    sheet_name="Olivine Profiles_WDS+EDS",
    header=52,
    index_col="DataSet/Point",
    engine="openpyxl",
)
# %%
Names = Ol_Profiles.Name.unique()
# %%


def get_C_prof(prof_name, DF, Element="Fo#"):
    prof = DF.loc[DF.Name == prof_name]
    distance_um = prof["Distance µm"]
    concentration = prof[Element]
    return distance_um.to_numpy(), concentration.to_numpy()


# %%
x, y = get_C_prof("AZ18_WHT06_ol41newname_prof_", Ol_Profiles)
# %%
for n in Names:
    x, y = get_C_prof(n, Ol_Profiles)
    if len(x) > 1:
        fig, ax = plt.subplots()
        plt.plot(x, y, marker="o", linestyle="dashed")
        plt.title(n)


# %%
for n in Names:
    x, y = get_C_prof(n, Ol_Profiles, Element="CaO")
    if len(x) > 1:
        fig, ax = plt.subplots()
        plt.plot(x, y, marker="o", linestyle="dashed")
        plt.title(n)

# %%
def plot_2_elements(Sample_name, element_1="Fo#", element_2="CaO"):

    fig, ax1 = plt.subplots()
    plt.title(Sample_name)
    color = "tab:red"
    ax1.set_xlabel("Micron (µm)")
    ax1.set_ylabel(element_1, color=color)

    x_1, y_1 = get_C_prof(Sample_name, Ol_Profiles, Element=element_1)
    ax1.plot(x_1, y_1, color=color, marker="o", linestyle="dashed")
    ax1.tick_params(axis="y", labelcolor=color)

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    color = "tab:blue"
    ax2.set_ylabel(element_2, color=color)
    x_2, y_2 = get_C_prof(Sample_name, Ol_Profiles, Element=element_2)
    ax2.plot(x_2, y_2, color=color, marker="s", linestyle="dashed")
    ax2.tick_params(axis="y", labelcolor=color)

    fig.tight_layout()  # otherwise the right y-label is slightly clipped

    return fig, ax1, ax2


# %%

for n in Names:
    x, y = get_C_prof(n, Ol_Profiles)
    if len(x) > 1:
        with PdfPages(n + " multielement_pdf.pdf") as pdf:
            fig, ax1, ax2 = plot_2_elements(
                Sample_name=n, element_1="Fo#", element_2="CaO"
            )
            pdf.savefig()
            plt.close()

            fig, ax1, ax2 = plot_2_elements(
                Sample_name=n, element_1="Al2O3", element_2="P2O5"
            )
            pdf.savefig()
            plt.close()

            fig, ax1, ax2 = plot_2_elements(
                Sample_name=n, element_1="NiO", element_2="MnO"
            )
            pdf.savefig()
            plt.close()

# %%

# Diffusion model constants # change eventually

# Give better pressures and fO2

fO2 = 1e-7  # 2.006191e-05 # Pa
EFo = 201000.0  # J/mol
P = 100000  # 200000000. # Pa
R = 8.3145  # J/molK
T = 1220 + 273.15  # T in kelvin

# %%
# Write a single function that takes all of these inputs and
sample = "AZ_WHT06_ol48_lasermount_xenocryst2_prof"

x, Fo = get_C_prof(sample, Ol_Profiles)
# Select these Parameters
D_FO_Func = D_Fo(
    T=T, P=P, fO2=fO2, alpha=90, beta=90, gamma=0, XFo=None, EFo=201000, R=8.3145
)

dx_micron = 1
dx = dx_micron * 1e-6  # m
dt = 60  # 100000
Di = D_FO_Func(0.8)
# Check for obeying the CFL Condition
CFL = (dt * Di) / (dx ** 2)
print(CFL)

Total_time = 30 * 24 * 60 * 60  # seconds
timesteps = int(Total_time / dt)

max_length = 60  # Profile length Microns
inflect_x = 25  # Microns to the inflection point

step_x, step_c = step_condition(
    ((0, inflect_x), (inflect_x, max_length)), (0.849, 0.882), dx_micron
)
bounds_c = (step_c[0], step_c[-1])
vector_c_in = step_c
vector_Fo_in = vector_c_in


Prof_length = np.max(step_x)  # µm
x_num = Prof_length / dx_micron

num = len(vector_c_in)
distance = np.linspace(0, dx_micron * (num), num)
# %%

Fo_diffusion_results = timestepper(
    vector_c_in=vector_c_in,
    vector_Fo_in=vector_Fo_in,
    diffusivity_function=D_FO_Func,
    bounds_c=bounds_c,
    timesteps=timesteps,
)

Fo_interp = interp.interp1d(x, Fo)
data_interp = Fo_interp(distance)

best_time, idx_min, sum_r2 = Best_fit_R2(Fo_diffusion_results, data_interp, dt)
best_time_days = seconds_to_days(best_time)

# %%
num = len(vector_c_in)
distance = np.linspace(0, dx_micron * (num), num)
fig, ax = plt.subplots(figsize=(12, 6))
plt.plot(distance, Fo_diffusion_results[idx_min], label="Best_fit_model")
plt.xlabel("Micron")
plt.ylabel("Fo")

plt.plot(x, Fo, label="Data")
plt.plot(step_x, step_c, Label="Initial Condition")
Title = sample
plt.title(Title)
model_time = "Best fit time: " + str(round(best_time_days, 2)) + " days"
plt.annotate(s=model_time, xy=(0.8, 0.05), xycoords="axes fraction")
plt.legend()
# %%


# %%
# Write a single function that takes all of these inputs and
sample = "AZ18_WHT06_ol43_xenocryst_Lasermount_prof_"

x, Fo = get_C_prof(sample, Ol_Profiles)
x = x[8:-1]
Fo = Fo[8:-1]
# Select these Parameters
D_FO_Func = D_Fo(
    T=T, P=P, fO2=fO2, alpha=90, beta=90, gamma=0, XFo=None, EFo=201000, R=8.3145
)

dx_micron = 1
dx = dx_micron * 1e-6  # m
dt = 60  # 100000
Di = D_FO_Func(0.8)
# Check for obeying the CFL Condition
CFL = (dt * Di) / (dx ** 2)
print(CFL)

Total_time = 30 * 24 * 60 * 60  # seconds
timesteps = int(Total_time / dt)

max_length = 120  # Profile length Microns
inflect_x = 37  # Microns to the inflection point

step_x, step_c = step_condition(
    ((0, inflect_x), (inflect_x, max_length)), (0.852, 0.895), dx_micron
)
bounds_c = (step_c[0], step_c[-1])
vector_c_in = step_c
vector_Fo_in = vector_c_in


Prof_length = np.max(step_x)  # µm
x_num = Prof_length / dx_micron

num = len(vector_c_in)
distance = np.linspace(0, dx_micron * (num), num)
# %%

Fo_diffusion_results = timestepper(
    vector_c_in=vector_c_in,
    vector_Fo_in=vector_Fo_in,
    diffusivity_function=D_FO_Func,
    bounds_c=bounds_c,
    timesteps=timesteps,
)

Fo_interp = interp.interp1d(x, Fo)
data_interp = Fo_interp(distance)

best_time, idx_min, sum_r2 = Best_fit_R2(Fo_diffusion_results, data_interp, dt)
best_time_days = seconds_to_days(best_time)

# %%
num = len(vector_c_in)
distance = np.linspace(0, dx_micron * (num), num)
fig, ax = plt.subplots(figsize=(12, 6))
plt.plot(distance, Fo_diffusion_results[idx_min], label="Best_fit_model")
plt.xlabel("Micron")
plt.ylabel("Fo")

plt.plot(x, Fo, label="Data")
plt.plot(step_x, step_c, Label="Initial Condition")
Title = sample
plt.title(Title)
model_time = "Best fit time: " + str(round(best_time_days, 2)) + " days"
plt.annotate(s=model_time, xy=(0.8, 0.05), xycoords="axes fraction")
plt.legend()
# %%


def Krige_Interpolate(X, Y, new_X):
    uk = OrdinaryKriging(
        X,
        np.zeros(X.shape),
        Y,
        pseudo_inv=True,
        weight=True,
        # nlags=3,
        # exact_values=False,
        variogram_model="linear",
        variogram_parameters={"slope": 3e-5, "nugget": 0.0002}
        # variogram_model="gaussian",
        # variogram_parameters={"sill": 1e2, "range": 1e2, "nugget": 0.0006},
    )

    y_pred, y_std = uk.execute("grid", new_X, np.array([0.0]), backend="loop")
    y_pred = np.squeeze(y_pred)
    y_std = np.squeeze(y_std)

    return new_X, y_pred, y_std


x, y = get_C_prof("AZ18_WHT06_ol41newname_prof_", Ol_Profiles, Element="Fo#")
step_x = np.arange(0, x.max(), 1)

X_interp, Y_Interp, Y_interp_std = Krige_Interpolate(x, y, step_x)

plt.plot(x, y, marker=".")
plt.plot(step_x, Y_Interp)
plt.plot(step_x, Y_Interp + 3 * Y_interp_std)
plt.plot(step_x, Y_Interp - 3 * Y_interp_std)
# %%

# %%
