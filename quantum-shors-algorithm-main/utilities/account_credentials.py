from qiskit_ibm_runtime import QiskitRuntimeService


def print_saved_accounts():
    print(QiskitRuntimeService.saved_accounts())

def save_ibm_cloud_account_credentials_fpc():
    print("Saving ibm cloud account credentials for FPC instance ...")
    QiskitRuntimeService.save_account(
        name='ibm_cloud_fpc',
        channel='ibm_cloud',
        token='',
        instance='',
        overwrite=True
    )

def save_ibm_cloud_account_credentials_free():
    print("Saving ibm cloud account credentials for FREE instance ...")
    QiskitRuntimeService.save_account(
        name='ibm_cloud_free',
        channel='ibm_cloud',
        token='',
        instance='',
        overwrite=True
    )

def save_ibm_quantum_account_credentials():
    print("Saving ibm quantum account credentials ...")
    QiskitRuntimeService.save_account(
        name='ibm_quantum',
        channel='ibm_quantum',
        token='',
        overwrite=True
    )

save_ibm_cloud_account_credentials_fpc()
save_ibm_cloud_account_credentials_free()
save_ibm_quantum_account_credentials()
# QiskitRuntimeService.delete_account(name='')
print_saved_accounts()