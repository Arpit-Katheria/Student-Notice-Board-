/* =========================================================
   DARK MODE
========================================================= */

const themeToggle =
    document.getElementById("themeToggle");

const savedTheme =
    localStorage.getItem("smartNoticeTheme");

if (savedTheme === "dark") {
    document.body.classList.add("dark-mode");
}

function updateThemeButton() {

    if (!themeToggle) return;

    themeToggle.textContent =
        document.body.classList.contains("dark-mode")
            ? "☀️"
            : "🌙";
}

updateThemeButton();


if (themeToggle) {

    themeToggle.addEventListener("click", () => {

        document.body.classList.toggle(
            "dark-mode"
        );

        localStorage.setItem(
            "smartNoticeTheme",
            document.body.classList.contains(
                "dark-mode"
            )
                ? "dark"
                : "light"
        );

        updateThemeButton();

    });
}


/* =========================================================
   SEARCH / FILTER
========================================================= */

const searchInput =
    document.getElementById("noticeSearch");

const categoryFilter =
    document.getElementById("categoryFilter");

const departmentFilter =
    document.getElementById("departmentFilter");

const priorityFilter =
    document.getElementById("priorityFilter");

const statusFilter =
    document.getElementById("statusFilter");

const sortSelect =
    document.getElementById("sortNotices");

const noticeList =
    document.getElementById("noticeList");

const noResults =
    document.getElementById("noSearchResults");


function filterNotices() {

    if (!noticeList) return;

    const notices = [
        ...noticeList.querySelectorAll(
            ".notice-item"
        )
    ];

    const search =
        searchInput?.value
            .trim()
            .toLowerCase() || "";

    const category =
        categoryFilter?.value || "all";

    const department =
        departmentFilter?.value || "all";

    const priority =
        priorityFilter?.value || "all";

    const status =
        statusFilter?.value || "all";

    let visible = 0;


    notices.forEach(notice => {

        const title =
            notice.dataset.title || "";

        const description =
            notice.dataset.description || "";

        const noticeCategory =
            notice.dataset.category || "";

        const noticeDepartment =
            notice.dataset.department || "";

        const noticePriority =
            notice.dataset.priority || "";

        const noticeStatus =
            notice.dataset.status || "";


        const searchMatch =
            !search ||
            title.includes(search) ||
            description.includes(search) ||
            noticeCategory
                .toLowerCase()
                .includes(search) ||
            noticeDepartment
                .toLowerCase()
                .includes(search);


        const categoryMatch =
            category === "all" ||
            noticeCategory === category;


        const departmentMatch =
            department === "all" ||
            noticeDepartment === department;


        const priorityMatch =
            priority === "all" ||
            noticePriority === priority;


        const statusMatch =
            status === "all" ||
            noticeStatus === status;


        const show =
            searchMatch &&
            categoryMatch &&
            departmentMatch &&
            priorityMatch &&
            statusMatch;


        notice.style.display =
            show ? "" : "none";


        if (show) {
            visible++;
        }

    });


    if (noResults) {

        noResults.classList.toggle(
            "hidden",
            visible !== 0
        );

    }
}


[
    searchInput,
    categoryFilter,
    departmentFilter,
    priorityFilter,
    statusFilter
].forEach(element => {

    if (!element) return;

    element.addEventListener(
        "input",
        filterNotices
    );

    element.addEventListener(
        "change",
        filterNotices
    );

});


/* =========================================================
   SORTING
========================================================= */

if (sortSelect) {

    sortSelect.addEventListener(
        "change",
        () => {

            if (!noticeList) return;

            const notices = [
                ...noticeList.querySelectorAll(
                    ".notice-item"
                )
            ];

            const mode =
                sortSelect.value;


            const priorityScore = {
                Urgent: 3,
                Important: 2,
                Normal: 1
            };


            notices.sort((a, b) => {

                if (mode === "smart") {

                    return (
                        Number(
                            b.dataset.score || 0
                        )
                        -
                        Number(
                            a.dataset.score || 0
                        )
                    );

                }


                if (mode === "views") {

                    return (
                        Number(
                            b.dataset.views || 0
                        )
                        -
                        Number(
                            a.dataset.views || 0
                        )
                    );

                }


                if (mode === "priority") {

                    return (
                        (
                            priorityScore[
                                b.dataset.priority
                            ] || 0
                        )
                        -
                        (
                            priorityScore[
                                a.dataset.priority
                            ] || 0
                        )
                    );

                }


                if (mode === "title") {

                    return (
                        a.dataset.title || ""
                    ).localeCompare(
                        b.dataset.title || ""
                    );

                }


                return (
                    Number(
                        b.dataset.created || 0
                    )
                    -
                    Number(
                        a.dataset.created || 0
                    )
                );

            });


            notices.forEach(notice => {

                noticeList.appendChild(
                    notice
                );

            });

            filterNotices();

        }
    );
}


/* =========================================================
   DELETE / TRASH MODAL
========================================================= */

const deleteModal =
    document.getElementById(
        "deleteModal"
    );

const confirmDelete =
    document.getElementById(
        "confirmDelete"
    );


function openDeleteModal(button) {

    if (!deleteModal) return;

    const url =
        button.dataset.deleteUrl;

    confirmDelete.href = url;

    if (url.includes("/delete/")) {

        confirmDelete.textContent =
            "Delete Permanently";

    } else {

        confirmDelete.textContent =
            "Move to Trash";

    }

    deleteModal.classList.add(
        "show"
    );

    document.body.classList.add(
        "modal-open"
    );
}


function closeDeleteModal() {

    if (!deleteModal) return;

    deleteModal.classList.remove(
        "show"
    );

    document.body.classList.remove(
        "modal-open"
    );
}


if (deleteModal) {

    deleteModal.addEventListener(
        "click",
        event => {

            if (
                event.target ===
                deleteModal
            ) {

                closeDeleteModal();

            }

        }
    );

}


document.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "Escape"
        ) {

            closeDeleteModal();

        }

    }
);


/* =========================================================
   BROWSER NOTIFICATIONS
========================================================= */

const notificationButton =
    document.getElementById(
        "notificationButton"
    );


if (
    notificationButton &&
    "Notification" in window
) {

    if (
        Notification.permission ===
        "granted"
    ) {

        notificationButton.textContent =
            "🔔 Notifications Enabled";

    }


    notificationButton.addEventListener(
        "click",
        async () => {

            const permission =
                await Notification.requestPermission();


            if (
                permission ===
                "granted"
            ) {

                notificationButton.textContent =
                    "🔔 Notifications Enabled";

                startNoticeWatcher();

            }

        }
    );

}


function startNoticeWatcher() {

    if (
        !("Notification" in window) ||
        Notification.permission !== "granted"
    ) {
        return;
    }


    setInterval(
        async () => {

            try {

                const response =
                    await fetch(
                        "/api/latest"
                    );

                const notices =
                    await response.json();


                if (!notices.length) {
                    return;
                }


                const newest =
                    notices[0];


                const lastSeen =
                    Number(
                        localStorage.getItem(
                            "lastNoticeId"
                        ) || 0
                    );


                if (
                    newest.id >
                    lastSeen
                ) {

                    new Notification(
                        "New Notice: " +
                        newest.title,
                        {
                            body:
                                newest.priority +
                                " notice published.",
                            icon:
                                "/static/icon.png"
                        }
                    );

                    localStorage.setItem(
                        "lastNoticeId",
                        newest.id
                    );

                }

            } catch (error) {

                console.log(
                    "Notification check failed."
                );

            }

        },
        30000
    );
}


if (
    "Notification" in window &&
    Notification.permission ===
    "granted"
) {

    startNoticeWatcher();

}


/* =========================================================
   INITIAL FILTER
========================================================= */

filterNotices();