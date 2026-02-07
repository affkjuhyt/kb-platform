export default function DashboardPage() {
    return (
        <div className="space-y-4">
            <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {/* Placeholder for dashboard stats */}
                <div className="p-4 border rounded-xl bg-card text-card-foreground shadow-sm">
                    <div className="text-sm font-medium text-muted-foreground">Total Documents</div>
                    <div className="text-2xl font-bold">12</div>
                </div>
                <div className="p-4 border rounded-xl bg-card text-card-foreground shadow-sm">
                    <div className="text-sm font-medium text-muted-foreground">Active Knowledge Bases</div>
                    <div className="text-2xl font-bold">3</div>
                </div>
            </div>
        </div>
    )
}
