#include <iostream>
#include <fstream>
#include <windows.h>
#include <winbio.h>

// Function to check if the program is running as an administrator
bool IsRunningAsAdmin() {
    BOOL isAdmin = FALSE;
    PSID adminGroup = NULL;

    // Allocate and initialize a SID for the administrators group
    SID_IDENTIFIER_AUTHORITY ntAuthority = SECURITY_NT_AUTHORITY;
    if (AllocateAndInitializeSid(&ntAuthority, 2,
        SECURITY_BUILTIN_DOMAIN_RID, DOMAIN_ALIAS_RID_ADMINS,
        0, 0, 0, 0, 0, 0, &adminGroup)) {

        CheckTokenMembership(NULL, adminGroup, &isAdmin);
        FreeSid(adminGroup);
    }

    return isAdmin;
}

void SaveFingerprintToFile(const WINBIO_BIR* sample, SIZE_T sampleSize) {
    std::ofstream file("fingerprint_data.bin", std::ios::binary);
    if (!file) {
        std::cerr << "Failed to open file for saving fingerprint data." << std::endl;
        return;
    }
    file.write(reinterpret_cast<const char*>(sample), sampleSize);
    file.close();
    std::cout << "Fingerprint data saved to 'fingerprint_data.bin'." << std::endl;
}

void CaptureFingerprint() {
    WINBIO_SESSION_HANDLE sessionHandle = NULL;
    WINBIO_UNIT_ID unitId = 0;
    WINBIO_REJECT_DETAIL rejectDetail = 0;
    WINBIO_BIR* sample = NULL;
    SIZE_T sampleSize = 0;
    HRESULT hr;

    // Open a biometric session with system pool
    hr = WinBioOpenSession(
        WINBIO_TYPE_FINGERPRINT,    // Biometric type
        WINBIO_POOL_SYSTEM,         // System pool
        WINBIO_FLAG_RAW,            // Access raw data
        NULL,                       // Array of biometric unit IDs
        0,                          // Count of biometric unit IDs
        NULL,                       // Database ID
        &sessionHandle              // [Out] Session handle
    );

    if (FAILED(hr)) {
        std::cerr << "Failed to open biometric session. Error: " << std::hex << hr << std::endl;
        return;
    }

    std::cout << "Biometric session opened successfully." << std::endl;

    // Capture a biometric sample
    hr = WinBioCaptureSample(
        sessionHandle,              // Session handle
        WINBIO_PURPOSE_ENROLL,      // Purpose: Enrollment
        WINBIO_DATA_FLAG_RAW,       // Raw data
        &unitId,                    // [Out] Unit ID
        &sample,                    // [Out] Sample data
        &sampleSize,                // [Out] Sample size
        &rejectDetail               // [Out] Reject detail
    );

    if (FAILED(hr)) {
        std::cerr << "WinBioCaptureSample failed. Error: " << std::hex << hr << std::endl;
        if (hr == E_ACCESSDENIED) {
            std::cerr << "Access denied. Please run the application with administrative privileges." << std::endl;
        }
        WinBioCloseSession(sessionHandle);
        return;
    }

    std::cout << "Fingerprint captured successfully!" << std::endl;

    // Save the fingerprint data to a file
    SaveFingerprintToFile(sample, sampleSize);

    // Free the captured sample memory
    if (sample != NULL) {
        WinBioFree(sample);
    }

    // Close the biometric session
    WinBioCloseSession(sessionHandle);
}

int main() {
    // Check if the application is running with administrative privileges
    if (!IsRunningAsAdmin()) {
        std::cerr << "This application requires administrative privileges. Please run as administrator." << std::endl;
        return 1;
    }

    // Ensure Windows Biometric Service is running
    SERVICE_STATUS_PROCESS ssStatus;
    DWORD dwBytesNeeded;
    SC_HANDLE schSCManager = OpenSCManager(NULL, NULL, SC_MANAGER_CONNECT);
    if (schSCManager == NULL) {
        std::cerr << "OpenSCManager failed. Error: " << GetLastError() << std::endl;
        return 1;
    }

    SC_HANDLE schService = OpenService(schSCManager, L"WbioSrvc", SERVICE_QUERY_STATUS);
    if (schService == NULL) {
        std::cerr << "OpenService failed. Error: " << GetLastError() << std::endl;
        CloseServiceHandle(schSCManager);
        return 1;
    }

    if (!QueryServiceStatusEx(schService, SC_STATUS_PROCESS_INFO, (LPBYTE)&ssStatus, sizeof(SERVICE_STATUS_PROCESS), &dwBytesNeeded)) {
        std::cerr << "QueryServiceStatusEx failed. Error: " << GetLastError() << std::endl;
        CloseServiceHandle(schService);
        CloseServiceHandle(schSCManager);
        return 1;
    }

    if (ssStatus.dwCurrentState != SERVICE_RUNNING) {
        std::cerr << "Windows Biometric Service is not running. Please start the service and try again." << std::endl;
        CloseServiceHandle(schService);
        CloseServiceHandle(schSCManager);
        return 1;
    }

    CloseServiceHandle(schService);
    CloseServiceHandle(schSCManager);

    // Proceed with fingerprint capture
    CaptureFingerprint();
    return 0;
}
